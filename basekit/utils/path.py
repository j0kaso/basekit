

import os
import errno
from os.path import basename, splitext, join, dirname



def ext( file_name ):
    return splitext( file_name )[1]

def stem( file_name ):
    return splitext( basename( file_name ) )[0]


def add_prefix( file_name, prefix="" ):
	return join( 
		dirname( file_name ), 
		prefix + basename( file_name ) 
	)

def add_suffix( file_name, suffix="" ):
	return join( 
        dirname( file_name ),
        stem( file_name ) + suffix + ext( file_name )
    )

def change_ext( file_name, extension="" ):
	return join( 
        dirname( file_name ),
        stem( file_name ) + "." + extension
    )

def mod( file_name, ext=None, prefix=None, suffix=None ):
	if ext:
		file_name = change_ext( file_name, ext )
	if prefix:
		file_name = add_prefix( file_name, prefix )
	if suffix:
		file_name = add_suffix( file_name, suffix )
	return file_name




def remove(filename):
    """silently remove a file"""
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise e
