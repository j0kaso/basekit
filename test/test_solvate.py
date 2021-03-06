import os
import unittest

from basekit import utils
from basekit import solvate


DIR = os.path.split( os.path.abspath( __file__ ) )[0]
PARENT_DIR = os.path.split( DIR )[0]
DATA_DIR = os.path.join( PARENT_DIR, "data", "test" )
TMP_DIR = os.path.join( DIR, "tmp" )

def data( file_name ):
    return os.path.join( DATA_DIR, file_name )

def tmp( *dir_name ):
    return os.path.join( TMP_DIR, "solvate", *dir_name )


@unittest.skipUnless( 
    utils.path.which( 'solvate' ), 'solvate cmd not found' )
class SolvateTestCase( unittest.TestCase ):
    def setUp( self ):
        inputfile = data( "bpti.pdb" )
        inputfile = inputfile.split('.pdb')[0]
        self.solvate = solvate.Solvate(
            inputfile,
            th=5.0,
            n=2,
            output_dir=tmp( "solvate" ),
            run=False,
            verbose=False
        )
    def test_check( self ):
        self.solvate()
        self.assertEquals( self.solvate.check( full=True ), "bpti_solvate.pdb" )