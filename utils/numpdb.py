from __future__ import division

import os
import operator
import functools
import itertools
import collections
from collections import defaultdict
from cStringIO import StringIO

import numpy as np

from utils import try_int, get_index
from math import dihedral, vec_dihedral, mag


# https://pypi.python.org/pypi/Bottleneck
# http://stutzbachenterprises.com/blist/


# http://sourceforge.net/p/pymmlib/code/HEAD/tree/trunk/pymmlib/mmLib/Superposition.py
# https://github.com/bryan-lunt/pdb_tools
# https://github.com/biopython/biopython/tree/master/Bio/PDB


# http://docs.scipy.org/doc/numpy/user/basics.io.genfromtxt.html
# http://docs.scipy.org/doc/numpy/reference/generated/numpy.genfromtxt.html
# TODO: using genfromtxt would require some preprocessing i.e. all non atom lines
#   need to be removed to parse the atom records; parsing a different
#   record then reqires another call to genfromtxt
# IDEA: option to read only backbone/ mainchain atoms


# PDB FORMAT SPECIFICATIONS
# http://deposit.rcsb.org/adit/docs/pdb_atom_format.html#ATOM
# http://www.cgl.ucsf.edu/chimera/docs/UsersGuide/tutorials/pdbintro.html

HELIX = 1
SHEET = 2


AA1 = {
    'HIS': 'H',
    'ARG': 'R',
    'LYS': 'K',
    'ILE': 'I',
    'PHE': 'F',
    'LEU': 'L',
    'TRP': 'W',
    'ALA': 'A',
    'MET': 'M',
    'PRO': 'P',
    'CYS': 'C',
    'ASN': 'N',
    'VAL': 'V',
    'GLY': 'G',
    'SER': 'S',
    'GLN': 'Q',
    'TYR': 'Y',
    'ASP': 'D',
    'GLU': 'E',
    'THR': 'T'
}
AA3 = dict((v,k) for k, v in AA1.iteritems())



class SimpleParser():
    def __init__( self ):
        self._list = []
    def __call__( self, line ):
        self._list.append( self._parse_line( line ) )
    def _test_line( self, line ):
        return len( line ) > 0
    def _parse_line( self, line ):
        return line
    def get( self ):
        if hasattr( self, "type" ):
            return np.array( self._list, dtype=self.type )
        return np.array( self._list )



pdb_delimiter=(6,5,1,4,1,3,1,1,4,1,3,8,8,8,6,6)
pdb_dtype=[
    ('record', '|S6'),          # 0
    ('atomno', np.int),         # 1
    ('empty1', '|S1'),          # 2
    ('atomname', '|S4'),        # 3
    ('altloc', '|S1'),          # 4
    ('resname', '|S3'),         # 5
    ('empty2', '|S1'),          # 6
    ('chain', '|S1'),           # 7
    ('resno', np.int),          # 8
    ('insertion', '|S1'),       # 9
    ('empty3', '|S3'),          # 10
    ('x', np.float),            # 11
    ('y', np.float),            # 12
    ('z', np.float),            # 13
    ('occupancy', np.float),    # 14
    ('bfac', np.float)          # 15
]
# pdb_usecols=(3,4,5,7,8,11,12,13)
pdb_usecols=(3,4,5,7,8,11,12,13)
pdb_cols=( 
    (0,6), (6,11), (11,12), (12,16), (16,17), (17,20), (20,21), (21,22), 
    (22,26), (26,27), (27,30), (30,38), (38,46), (46,54), (54,60), (60,66)
)



class SstrucParser( SimpleParser ):
    def __init__( self ):
        self._list = []
    def __call__( self, line ):
        self._list.append( self._parse_line( line ) )
    def _test_line( self, line ):
        return line.startswith("HELIX") or line.startswith("SHEET")
    def _parse_line( self, line ):
            if line.startswith("HELIX"):
                return [
                    HELIX,
                    line[19],                   # chain 1
                    try_int( line[21:25] ),     # resno 1
                    line[31],                   # chain 2
                    try_int( line[33:37] ),     # resno 2
                    try_int( line[38:40] ),     # subtype
                    None                        # padding...
                ]
            elif line.startswith("SHEET"):
                return [
                    SHEET,
                    line[21],                   # chain 1
                    try_int( line[22:26] ),     # resno 1
                    line[32],                   # chain 2
                    try_int( line[33:37] ),     # resno 2
                    try_int( line[38:40] ),     # strand sense (subtype)
                    try_int( line[65:69] ),     # resno hbond prev strand
                ]
    def get( self ):
        self._list.sort( key=operator.itemgetter(1,2) )
        return self._list



def sstruc2jmol( sstruc ):
    ret = ""
    for i, ss in enumerate( sstruc ):
        ret += "draw ID 'v%i' vector {%s} {%s};" % (
            i,
            "%0.2f %0.2f %0.2f" % tuple(ss[8]),
            "%0.2f %0.2f %0.2f" % tuple(ss[7])
        )
    return ret

def lsq(y):
    # y = mx + c
    x = np.arange( len(y) )
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq( A, y )[0]
    return [ m*x[0]+c, m*x[-1]+c ]

def axis( coords ):
    return np.array([ lsq(coords[...,i]) for i in range(3) ]).T


        


class NumAtoms:
    atomname_dict = { 
        "CA": " CA ",
        "N": " N  ",
        "C": " C  ",
        "O": " O  ",
        "backbone": ( " CA ", " N  ", " C  ", " O  " ),
        "mainchain": ( " CA ", " N  ", " C  " )
    }
    def __init__( self, atoms, coords, flag=None ):
        self._atoms = atoms
        self._coords = coords
        self.flag = flag
        self.length = len( atoms )
    def __getitem__( self, key ):
        if key=='xyz':
            return self._coords
        else:
            return self._atoms[ key ]
    def __setitem__( self, key, value ):
        if key=='xyz':
            self._coords = value
        else:
            self._atoms[ key ] = value
    def sele( self, chain=None, resno=None, atomname=None, sele=None ):
        atoms = self._atoms
        if sele==None:
            sele = np.ones( self.length, bool )
        if chain!=None:
            if isinstance( chain, (list, tuple) ):
                sele &= reduce( 
                    lambda x, y: x | (atoms['chain']==y), 
                    chain[1:],
                    atoms['chain']==chain[0]
                )
            else:
                sele &= atoms['chain']==chain
        if resno!=None:
            if isinstance( resno, (list, tuple) ):
                sele &= (atoms['resno']>=resno[0]) & (atoms['resno']<=resno[1])
            else:
                sele &= atoms['resno']==resno
        if atomname!=None:
            
            if isinstance( atomname, (list, tuple) ):
                atomname = [ self.atomname_dict.get( a, a ) for a in atomname ]
                sele &= reduce( 
                    lambda x, y: x | (atoms['atomname']==y), 
                    atomname[1:],
                    atoms['atomname']==atomname[0]
                )
            else:
                atomname = self.atomname_dict.get( atomname, atomname )
                sele &= atoms['atomname']==atomname
        return sele
    def slice( self, begin, end, flag=None ):
        return NumAtoms( self._atoms[begin:end], self._coords[begin:end], flag=flag )
    def copy( self, **sele ):
        _sele = self.sele( **sele )
        return NumAtoms( self._atoms[ _sele ], self._coords[ _sele ] )
    def get( self, key, **sele ):
        if key=='xyz':
            return self._coords[ self.sele( **sele ) ]
        else:
            return self._atoms[ self.sele( **sele ) ][ key ]
    def iter_chain( self, **sele ):
        if len(sele):
            _sele = self.sele( **sele )
            atoms = self._atoms[ _sele ]
            coords = self._coords[ _sele ]
        else:
            atoms = self._atoms
            coords = self._coords
        
        chain = atoms['chain'][0]
        k = 0
        l = 0
        for a in atoms:
            if chain!=a['chain']:
                yield self.slice( k, l )
                chain = a['chain']
                k = l
            l += 1
        yield self.slice( k, l )
    def iter_resno( self, **sele ):
        for numatoms in self.iter_chain( **sele ):
            resno = numatoms['resno'][0]
            atoms = numatoms._atoms
            k = 0
            l = 0
            flag = True
            for a in atoms:
                if resno!=a['resno']:
                    yield numatoms.slice( k, l, flag=flag )
                    k = l
                    # detect chain breaks
                    flag = True if (resno!=a['resno']-1) else False
                    resno = a['resno']
                l += 1
            yield numatoms.slice( k, l, flag=flag )
    def iter_resno2( self, window, **sele ):
        # TODO assumes the first a has a[2]=True and
        #   the first results window has no additional a[2]=True
        it = self.iter_resno( **sele )
        for a in it:
            if a.flag:
                result = (a,) + tuple(itertools.islice(it, window-1))
            else:
                result = result[1:] + (a,)
            yield result
    def axis( self, **sele ):
        return axis( self.get( 'xyz', **sele ) )
    def sequence( self, **sele ):
        return "".join([ AA1.get( a['resname'][0], "?" ) for a in self.iter_resno( **sele ) ])
    def dist( self, sele1, sele2 ):
        coords1 = self.get( 'xyz', **sele1 )
        coords2 = self.get( 'xyz', **sele2 )
        v1 = np.sum( coords1, axis=0 ) / len(coords1)
        v2 = np.sum( coords2, axis=0 ) / len(coords2)
        return mag( v1 - v2 )




class NumPdb:
    def __init__( self, pdb_path, features=None ):
        self.pdb_path = pdb_path
        self.features = features or {
            "phi_psi": True,
            "sstruc": True
        }
        self._set_parsers()
        self._parse()
    def __getitem__( self, key ):
        return self.numatoms[ key ]
    def _set_parsers( self ):
        self._parsers = {
            #"sstruc": SstrucParser()
        }
    def _parse( self ):
        cols = []
        types = []
        for j, c in enumerate(pdb_usecols):
            cols.append( pdb_cols[c] )
            types.append( pdb_dtype[c] )

        extra = []
        if self.features["phi_psi"]:
            types += [ ( 'phi', np.float ), ( 'psi', np.float ) ]
            extra += [ np.nan, np.nan ]
        if self.features["sstruc"]:
            types += [ ( 'sstruc', '|S1' ) ]
            extra += [ np.nan ]

        atoms = []
        header = []

        with open( self.pdb_path, "r" ) as fp:
            for line in fp:
                if line.startswith("ATOM"):# or line.startswith("HETATM"):
                    atoms.append( tuple([ line[ c[0]:c[1] ] for c in cols ] + extra) )
                else:
                    header.append( line )
        
        atoms = np.array(atoms, dtype=types)
        coords = np.vstack(( atoms['x'], atoms['y'], atoms['z'] )).T
        # print np.may_share_memory( self.atoms, self.coords )
        # print self.atoms.flags.owndata, self.coords.flags.owndata

        self.numatoms = NumAtoms( atoms, coords )

        self.length = len( atoms )
        if self.features["phi_psi"]:
            self.__calc_phi_psi()
        if self.features["sstruc"]:
            self.__calc_sstruc()
    
    @property
    def sstruc( self ):
        for i, ss in enumerate( self._sstruc ):
            a = self.axis( sstruc=i )
            ss.extend([ a[1]-a[0], a[0], a[1], i+1 ])
        return self._sstruc
    def iter_chain( self, **sele ):
        return self.numatoms.iter_chain( **sele )
    def iter_resno( self, **sele ):
        return self.numatoms.iter_resno( **sele )
    def iter_resno2( self, window, **sele ):
        return self.numatoms.iter_resno2( window, **sele )
    def __calc_sstruc( self ):
        pass
    def __calc_phi_psi( self ):

        sele = { "atomname": ["N", "CA", "C"] }

        for na_prev, na_curr, na_next in self.iter_resno2( 3 ):

            if na_prev.flag:
                xyz_n_prev, xyz_ca_prev, xyz_c_prev = na_prev.get( 'xyz', **sele )
                xyz_n, xyz_ca, xyz_c = na_curr.get( 'xyz', **sele )
                xyz_n_next, xyz_ca_next, xyz_c_next = na_next.get( 'xyz', **sele )
                na_prev['psi'] = dihedral( xyz_n_prev, xyz_ca_prev, xyz_c_prev, xyz_n )
                na_curr['phi'] = dihedral( xyz_c_prev, xyz_n, xyz_ca, xyz_c )
            else:
                xyz_n, xyz_ca, xyz_c = xyz_n_ca_c
                xyz_n_next, xyz_ca_next, xyz_c_next = na_next.get( 'xyz', **sele )
            
            na_next['phi'] = dihedral( xyz_c, xyz_n_next, xyz_ca_next, xyz_c_next )
            na_curr['psi'] = dihedral( xyz_n, xyz_ca, xyz_c, xyz_n_next )
            xyz_n_ca_c = ( xyz_n_next, xyz_ca_next, xyz_c_next )
        #for a in self._atoms: print a
    def dist( self, sele1, sele2 ):
        return self.numatoms.dist( sele1, sele2 )
    def sequence( self, **sele ):
        return self.numatoms.sequence( **sele )





