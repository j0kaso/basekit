#! /usr/bin/env python

"""A collection of MPPD tools"""

from basekit.utils.tool import parse_subargs
from basekit.mppd import MppdPipeline, MppdStats




def main():
    tools = {
        "pdb": MppdPipeline,
        "stats": MppdStats
    }
    Tool, args, kwargs = parse_subargs( tools, description=__doc__ )
    print Tool( *args, **kwargs )



if __name__ == "__main__":
    main()