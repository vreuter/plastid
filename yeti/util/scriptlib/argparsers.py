#!/usr/bin/env python
"""This module contains pairs of functions that enable command-line scripts
to open and process various types of data. 

Capabilities provided include:

    Importing read alignments or counts
        :py:func:`get_alignment_file_parser`
            Create an :py:class:`~argparse.ArgumentParser` that reads alignment
            or count data from BAM, Bowtie, Wiggle, and BEDGraph files
    
        :py:func:`get_genome_array_from_args`
            Returns a |GenomeArray|, |SparseGenomeArray|, or |BAMGenomeArray|,
            from arguments parsed by a parser from :py:func:`get_alignment_file_parser`,
            applying read mapping transformations as appropriate

    Importing transcript models
        :py:func:`get_annotation_file_parser`
            Create an :py:class:`~argparse.ArgumentParser` that reads transcript 
            models from GTF2, GFF3, and BED  annotation files
            
        :py:func:`get_transcripts_from_args`
            Returns a list of |Transcript| objects parsed from arguments parsed
            by a parser made by :py:func:`get_annotation_file_parser`

    Importing arbitrary regions of interest
        :py:func:`get_segmentchain_file_parser`
            Create an :py:class:`~argparse.ArgumentParser` that can import 
            SegmentChains from GTF2, GFF3, BED, and PSL (blat) files

        :py:func:`get_segmentchains_from_args`
            Returns a list of |SegmentChain| objects from arguments
            parsed by a parser made by :py:func:`get_segmentchain_file_parser`

    Hashing regions of the genome that should be excluded from analyses
        :py:func:`get_mask_file_parser`
            Open an annotation file in GTF2, GFF3, BED, or PSL format
             
        :py:func:`get_genome_hash_from_mask_args`
            Return a |GenomeHash| of genomic regions to mask from analyses
            
To add any these capabilities to your command line scripts, import the corresponding
function pair above. Use the first function in each pair to create an 
:py:class:`~argparse.ArgumentParser`, and supply this object as a *parent* to your script's
internal :py:class:`~argparse.ArgumentParser`. Then, use the second function to
parse the arguments.

Your script will then be able process various sorts  of count/alignment and annotation files
from the arguments.

Examples
--------
Write a script that can import transcript annotations from BED, BigBed, GFF3, and GTF2 files::

    import argparse
    from yeti.util.scriptlib.argparsers import get_annotation_file_parser, get_transcripts_from_args

    # create annotation file parser
    annotation_file_parser = get_annotation_file_parser(disabled=["some_option"])
    
    # create my own parser, incorporating flags from annotation_file_parser
    my_own_parser = argparse.ArgumentParser(parents=[annotation_file_parser])
    
    # add script-specific arguments
    my_own_parser.add_argument("--foo",type=int,default=5,help="Some option")
    my_own_parser.add_argument("--bar",type=str,default="a string",help="Another option")
    
    # parse args
    args = parser.parse_args()
    
    # get transcript objects from arguments
    transcripts,rejected = get_transcripts_from_args(args)
    
    ...
    
    # rest of your script
    

See Also
--------
:py:mod:`argparse`
    Python documentation on argument parsing

:py:mod:`~yeti.genomics.genome_array`
    Data structures for import of read alignments or counts

:py:mod:`~yeti.genomics.roitools`
    Data structures describing transcripts or genomic regions of interest

:py:mod:`~yeti.genomics.genome_hash`
    Fetch feature annotations overlapping genomic regions of interest

:py:obj:`yeti.bin`
    Source code of command-line scripts, for further examples
"""
import argparse
import pysam
import sys
from collections import OrderedDict
from yeti.util.services.exceptions import MalformedFileError
from yeti.genomics.genome_array import GenomeArray, SparseGenomeArray,\
                                           BAMGenomeArray,\
                                           SizeFilterFactory, NibbleMapFactory,\
                                           FivePrimeMapFactory, ThreePrimeMapFactory,\
                                           VariableFivePrimeMapFactory,\
                                           five_prime_map,  \
                                           three_prime_map, \
                                           entire_map,      \
                                           center_map,      \
                                           five_prime_variable_map

from yeti.readers.gff import GFF3_TranscriptAssembler, GTF2_TranscriptAssembler
from yeti.readers.bed import BED_Reader
from yeti.readers.bigbed import BigBedReader
from yeti.readers.psl import PSL_Reader
from yeti.genomics.roitools import SegmentChain, Transcript
from yeti.genomics.genome_hash import GenomeHash, BigBedGenomeHash, TabixGenomeHash
from yeti.util.io.openers import opener, NullWriter
from yeti.util.io.filters import CommentReader

from yeti.readers.gff import _DEFAULT_GFF3_GENE_TYPES,\
                             _DEFAULT_GFF3_TRANSCRIPT_TYPES,\
                             _DEFAULT_GFF3_EXON_TYPES,\
                             _DEFAULT_GFF3_CDS_TYPES


#===============================================================================
# INDEX: String constants used in parsers below
#===============================================================================

_MAPPING_RULE_DESCRIPTION = """For BAM or bowtie files, one of the mutually exclusive read mapping choices
(`fiveprime_variable`, `fiveprime`, `threeprime`, or `center`) is required.
`'--offset`, `--nibble`, `--min_length` and `--max_length` are optional."""

_DEFAULT_ALIGNMENT_FILE_PARSER_DESCRIPTION = "Open alignment or count files and optionally set mapping rules"
_DEFAULT_ALIGNMENT_FILE_PARSER_TITLE = "alignment mapping rules (for BAM & bowtie files)"

_DEFAULT_ANNOTATION_PARSER_DESCRIPTION = "Open one or more genome annotation files"
_DEFAULT_ANNOTATION_PARSER_TITLE = "annotation file options (one or more annotation files required)"

_MASK_PARSER_TITLE = "mask file options (optional)"
_MASK_PARSER_DESCRIPTION = """Add mask file(s) that annotate regions that should be excluded from analyses
(e.g. repetitive genomic regions)."""


#===============================================================================
# INDEX: Alignment/count file parser, and helper functions
#===============================================================================


def get_alignment_file_parser(input_choices=("BAM","bowtie","wiggle"),
                              disabled=[],
                              prefix="",
                              title=_DEFAULT_ALIGNMENT_FILE_PARSER_TITLE,
                              description=_DEFAULT_ALIGNMENT_FILE_PARSER_DESCRIPTION,
                              return_subparsers=False):
    """Return an :py:class:`~argparse.ArgumentParser` that opens
    alignment (BAM or bowtie) or count (Wiggle, BEDGraph) files.
     
    In the case of bowtie or BAM import, read mapping rules (e.g. fiveprime end mapping,
    threeprime end mapping, et c) and read length filters may be applied.
    
    Parameters
    ----------
    input_choices : list, optional
        list of permitted alignment file type choices
        
    disabled : list, optional
        list of parameter names that should be disabled from parser,
        without preceding dashes

    prefix : str, optional
        string prefix to add to default argument options (Default: "")
    
    title : str, optional
        title for option group (used in command-line help screen)
            
    description : str, optional
        description of parser (used in command-line help screen)
        
    return_subparsers : bool, optional
        if True, additionally return a dictionary of subparser option groups,
        to which additional options may be added (Default: False)
            
    Returns
    -------
    argparse.ArgumentParser
    
    
    See also
    --------
    get_genome_array_from_args
        function that parses the :py:class:`~argparse.Namespace`
        returned by this :py:class:`~argparse.ArgumentParser`
    """

    # pardon the long line. it is essential for Sphinx
 
    alignment_file_parser = argparse.ArgumentParser(description=description,
                                                    add_help=False)

    subparsers = { }
    if len({ "BAM", "bowtie" } & set(input_choices)) > 0:
        subparsers["mapping"] = alignment_file_parser.add_argument_group(title=title,
                                                           description=_MAPPING_RULE_DESCRIPTION)
        
        # dictionary of options for mapping. Defined initially as a dict
        # so we can disable anything programmatically above
        map_option_dict = OrderedDict([
                            ("fiveprime_variable" , dict(action="store_const",
                                                        const="fiveprime_variable",
                                                        dest="%smapping" % prefix,
                                                        help="Map read alignment to a variable offset from 5' position of read, "+
                                                             "with offset determined by read length. Requires `--offset` below")),
                            ("fiveprime"        , dict(action="store_const",
                                                        const="fiveprime",
                                                        dest="%smapping" % prefix,
                                                        help="Map read alignment to 5' position.")),
                            ("threeprime"       , dict(action="store_const",
                                                        const="threeprime",
                                                        dest="%smapping" % prefix,
                                                        help="Map read alignment to 3' position")),
                            ("center"           , dict(action="store_const",
                                                        const="center",
                                                        dest="%smapping" % prefix,
                                                        help="Subtract N positions from each end of read, "+
                                                             "and add 1/(length-N), to each remaining position, "+
                                                             "where N is specified by `--nibble`")),
                            ("offset"           , dict(default=0,
                                                        metavar="OFFSET",
                                                        help="For `--fiveprime` or `--threeprime`, provide an integer "+
                                                          "representing the offset into the read, "+
                                                          "starting from either the 5\' or 3\' end, at which data "+
                                                          "should be plotted. For `--fiveprime_variable`, "+
                                                          "provide the filename of a two-column tab-delimited text "+
                                                          "file, in which first column represents read length or the "+
                                                          "special keyword `'default'`, and the second column represents "+
                                                          "the offset from the five prime end of that read length at which the read should be mapped.")),
                            ("nibble"           , dict(type=int,
                                                        default=0,
                                                        metavar="N",
                                                        help="For use with `--center` only. nt to remove from each "+
                                                             "end of read before mapping (Default: 0)")),
                            ("min_length"       , dict(type=int,
                                                       default=25,
                                                       metavar="N",
                                                       help="Minimum read length required to be included"+
                                                            " (Default: 25)")),
                            ("max_length"       , dict(type=int,
                                                       default=100,
                                                       metavar="N",
                                                       help="Maximum read length permitted to be included"+
                                                            " (Default: 100)")),
                            ])

        for k,v in filter(lambda x: x[0] not in disabled,map_option_dict.items()):
            subparsers["mapping"].add_argument("--%s%s" % (prefix,k),**v)

    alignment_option_dict = OrderedDict([
                        ("count_files"     , dict(type=str,
                                                  default=[],
                                                  nargs="+",
                                                  help="Count or alignment file(s).")),
                        ("countfile_format", dict(choices=input_choices,
                                                  default="BAM",
                                                  help="Format of file containing alignments or counts (default: BAM)")),
                        ("big_genome"       , dict(action="store_true",
                                                   default=False,
                                                   help="Use slower but memory-efficient implementation "+
                                                        "for big genomes (e.g. >20 megabases; irrelevant "+
                                                        "for BAM files), or for memory-limited computers")),
                        ("normalize"        , dict(action="store_true",
                                                   help="Whether counts should be normalized"+
                                                        " to counts per million (usually not. default: False)",
                                                   default=False)),
                        ])

    for k,v in filter(lambda x: x[0] not in disabled,alignment_option_dict.items()):
        alignment_file_parser.add_argument("--%s%s" % (prefix,k),**v)

    if return_subparsers == True:
        return alignment_file_parser, subparsers
    else:
        return alignment_file_parser


def get_genome_array_from_args(args,prefix="",disabled=[],printer=NullWriter()):
    """Return a |GenomeArray|, |SparseGenomeArray| or |BAMGenomeArray|
    from arguments parsed by :py:func:`get_alignment_file_parser`
    
    Parameters
    ----------
    args : :py:class:`argparse.Namespace`
        Namespace object from :py:func:`get_alignment_file_parser`

    prefix : str, optional
        string prefix to add to default argument options (Default: "")
        Must be same prefix that was added in call to :py:func:`get_alignment_file_parser`
        (Default: "")

    disabled : list, optional
        list of parameter names that were disabled when the argparser was created
        in :py:func:`get_alignment_file_parser`. (Default: ``[]``)
        
    printer : file-like, optional
        A stream to which stderr-like info can be written (default: |NullWriter|) 
    
    
    Returns
    -------
    |GenomeArray|, |SparseGenomeArray|, or |BAMGenomeArray|
    
    
    See Also
    --------
    get_alignment_file_parser
        Function that creates :py:class:`~argparse.ArgumentParser` whose output
        :py:class:`~argparse.Namespace` is processed by this function        
    """
    args = PrefixNamespaceWrapper(args,prefix)
    
    # require at least one countfile
    if len(args.count_files) == 0:
        printer.write("Please include at least one input file.")
        sys.exit(1)
    
    # require mapping rules unless wiggle
    if args.mapping is None and args.countfile_format != "wiggle":
        printer.write("Please specify a read mapping rule.")
        sys.exit(1)
    
    if "countfile_format" not in disabled and args.countfile_format == "BAM":
        count_files = [pysam.Samfile(X,"rb") for X in args.count_files]
        try:
            gnd = BAMGenomeArray(count_files)
        except ValueError:
            printer.write("Input BAM file(s) not indexed. Please index via:")
            printer.write("")
            for fn in args.count_files:
                printer.write("    samtools index %s" % fn)
            printer.write("")
            printer.write("Exiting.")
            sys.exit(1)
            
        size_filter = SizeFilterFactory(min=args.min_length,max=args.max_length)
        gnd.add_filter("size:%s-%s" % (args.min_length,args.max_length) ,size_filter)
        if args.mapping == "fiveprime":
            map_function = FivePrimeMapFactory(int(args.offset))
        elif args.mapping == "threeprime":
            map_function = ThreePrimeMapFactory(int(args.offset))
        elif args.mapping == "center":
            map_function = NibbleMapFactory(args.nibble)
        elif args.mapping == "fiveprime_variable":
            if str(args.offset) == "0":
                printer.write("Please specify a filename to use for fiveprime variable offsets in --offset.")
                sys.exit(1)
            offset_dict = _parse_variable_offset_file(CommentReader(open(args.offset)))
            map_function = VariableFivePrimeMapFactory(offset_dict)
        gnd.set_mapping(map_function)
        
        
    else:
        if "big_genome" not in disabled and args.big_genome == True:
            gnd = SparseGenomeArray()
        else:
            gnd = GenomeArray()
            
        if "countfile_format" not in disabled and args.countfile_format == "wiggle":
            for align_file in args.count_files:
                printer.write("Opening wiggle files %s..." % align_file)
                with open("%s_fw.wig" % align_file) as fh:
                    gnd.add_from_wiggle(fh,"+")
                with open("%s_rc.wig" % align_file) as fh:
                    gnd.add_from_wiggle(fh,"-")
        else:
            trans_args = { "nibble" : int(args.nibble) }
            if args.mapping == "fiveprime_variable":
                transformation = five_prime_variable_map
                if str(args.offset) == "0":
                    printer.write("Please specify a filename to use for fiveprime variable offsets in --offset.")
                    sys.exit(1)
                else:
                    with open(args.offset) as myfile:
                        trans_args["offset"] = _parse_variable_offset_file(CommentReader(myfile))
            else:
                trans_args["offset"] = int(args.offset)
                if args.mapping == "fiveprime":
                    transformation = five_prime_map
                elif args.mapping == "threeprime":
                    transformation = three_prime_map
                elif args.mapping == "entire":
                    transformation = entire_map
                elif args.mapping == "center":
                    transformation = center_map
                else:
                    transformation = entire_map
        
            for infile in args.count_files:
                with opener(infile) as my_file:
                    if args.countfile_format == "bowtie":
                        gnd.add_from_bowtie(my_file,transformation,min_length=args.min_length,max_length=args.max_length,**trans_args)
        
        printer.write("Counted %s total reads..." % gnd.sum())
        
    if "normalize" not in disabled and args.normalize == True:
        printer.write("Normalizing to reads per million...")
        gnd.set_normalize(True)
    
    return gnd


#===============================================================================
# INDEX: Annotation file parser, and helper functions
#===============================================================================


def get_annotation_file_parser(input_choices=["BED","BigBed","GTF2","GFF3"],
                               disabled=[],
                               prefix="",
                               title=_DEFAULT_ANNOTATION_PARSER_TITLE,
                               description=_DEFAULT_ANNOTATION_PARSER_DESCRIPTION,
                               return_subparsers=False):
    """Return an :py:class:`~argparse.ArgumentParser` that opens
    annotation files from BED, GTF2, or GFF3 formats
     
    In the case of bowtie or BAM import, read mapping rules (e.g. fiveprime end mapping,
    threeprime end mapping, et c) and read length filters may be applied.
    
    Parameters
    ----------
    input_choices : list, optional
        list of permitted alignment file type choices.
        (Default: ["BED","BigBed","GTF2","GFF3"]). PSL may also be added
        
    disabled : list, optional
        list of parameter names that should be disabled from parser
        without preceding dashes

    prefix : str, optional
        string prefix to add to default argument options (Default: "")
    
    title : str, optional
        title for option group (used in command-line help screen)
        
    description : str, optional
        description of parser (used in command-line help screen)
    
    return_subparsers : bool, optional
        if True, additionally return a dictionary of subparser option groups,
        to which additional options may be added (Default: False)
    
    Returns
    -------
    argparse.ArgumentParser
    
    
    See also
    --------
    get_transcripts_from_args
        function that parses the :py:class:`~argparse.Namespace` returned
        by this :py:class:`~argparse.ArgumentParser`
    """
    annotation_file_parser = argparse.ArgumentParser(add_help=False)
    """Open genome annotation files in %s format""" % ", ".join(input_choices)
    
    subparsers = { "annotation" : annotation_file_parser.add_argument_group(title=title,description=description) }

    option_dict = OrderedDict([
                    ("annotation_files"     , dict(metavar="infile.[%s]" % " | ".join(input_choices),# | psl]",
                                                  type=str,nargs="+",default=[],
                                                  help="Zero or more annotation files (max 1 file if BigBed)")),                               
                    ("annotation_format"   , dict(choices=input_choices,
                                                  default="GTF2",
                                                  help="Format of %sannotation_files (default: GTF2). Note: GFF3 assembly assumes SO v.2.5.2 feature ontologies, which may or may not match your specific file." % prefix)),    
                    ("add_three"           , dict(default=False,
                                                  action="store_true",
                                                  help="If supplied, coding regions will be extended by 3 nucleotides at their 3\' ends (except for GTF2 files that explicitly include `stop_codon` features). Use if your annotation file excludes stop codons from CDS.")),
                    ("tabix"               , dict(default=False,
                                                  action="store_true",
                                                  help="%sannotation_files are tabix-compressed and indexed (Default: False). Ignored for BigBed files." % prefix)),
                   ])
    if "GFF3" in input_choices:
        option_dict["gff_transcript_types"] = dict(type=str,
                                                  default=_DEFAULT_GFF3_TRANSCRIPT_TYPES,
                                                  nargs="+",
                                                  help="GFF3 feature types to include as transcripts, even "+\
                                                 "if no exons are present (for GFF3 only; default: use SO v2.5.3 specification)")
        option_dict["gff_exon_types"] =       dict(type=str,
                                                  default=_DEFAULT_GFF3_EXON_TYPES,
                                                  nargs="+",
                                                  help="GFF3 feature types to include as exons (for GFF3 only; default: use SO v2.5.3 specification)")
        option_dict["gff_cds_types"] =       dict(type=str,
                                                  default=_DEFAULT_GFF3_CDS_TYPES,
                                                  nargs="+",
                                                  help="GFF3 feature types to include as CDS (for GFF3 only; default: use SO v2.5.3 specification)")
        
    for k,v in filter(lambda x: x[0] not in disabled,option_dict.items()):
        subparsers["annotation"].add_argument("--%s%s" % (prefix,k),**v)
    
    if return_subparsers == True:
        return annotation_file_parser, subparsers
    else:
        return annotation_file_parser

def get_transcripts_from_args(args,prefix="",disabled=[],printer=NullWriter(),return_type=Transcript):
    """Return a list of |Transcript| objects from arguments parsed by :py:func:`get_annotation_file_parser`
    
    Parameters
    ----------
    args : :py:class:`argparse.Namespace`
        Namespace object from :py:func:`get_annotation_file_parser`
    
    prefix : str, optional
        string prefix to add to default argument options.
        Must be same prefix that was added in call to :py:func:`get_annotation_file_parser`
        (Default: "")
        
    disabled : list, optional
        list of parameter names that were disabled when the annotation file
        parser was created by :py:func:`get_annotation_file_parser`. 
        (Default: ``[]``)
            
    printer : file-like, optional
        A stream to which stderr-like info can be written (default: |NullWriter|) 
    
    return_type : |SegmentChain| of subclass, optional
        Type of object to return (Default: |Transcript|)
    
    Returns
    -------
    iterator
        |Transcript| objects, either in order of appearance (if input was a BED or PSL file),
        or sorted lexically by chromosome, start coordinate, end coordinate,
        and then strand (if input was) GTF or GFF
    
    
    See Also
    --------
    get_annotation_file_parser
        Function that creates :py:class:`argparse.ArgumentParser` whose output
        :py:class:`~argparse.Namespace` is processed by this function    
    """
    if prefix != "":
        args = PrefixNamespaceWrapper(args,prefix)

    printer.write("Parsing features in %s..." % ", ".join(args.annotation_files))
    
    if "tabix" not in disabled:
        tabix = args.tabix
    else:
        tabix = False
        
    if "add_three" not in disabled:
        add_three = args.add_three
    else:
        add_three = False
    
    if args.annotation_format.lower() == "bigbed":
        if len(args.annotation_files) > 1:
            printer.write("Bad arguments: we can only process one BigBed file.")
            sys.exit(2)
        if tabix == True:
            printer.write("Tabix compression is incompatible with BigBed files. Ignoring.")
        transcripts = BigBedReader(args.annotation_files[0],
                                   return_type=Transcript,
                                   cache_depth=1,
                                   add_three_for_stop=add_three,
                                   printer=printer)
        
    elif tabix == True:
        #streams = [pysam.tabix_iterator(opener(X), lambda x,y: x) for X in args.annotation_files] # used to work in earlier pysam
        # string parsing by supplying None instead of `asTuple()` no longer works
        # nor do anonymous lambda functions
        streams = [pysam.tabix_iterator(opener(X), pysam.asTuple()) for X in args.annotation_files]
    else:
        streams = (opener(X) for X in args.annotation_files)
    
    if args.annotation_format.lower() == "gff3":
        transcripts = GFF3_TranscriptAssembler(*streams,
                                               transcript_types=args.gff_transcript_types,
                                               exon_types=args.gff_exon_types,
                                               cds_types=args.gff_cds_types,
                                               printer=printer,
                                               add_three_for_stop=add_three,
                                               tabix=tabix)
    elif args.annotation_format.lower() == "gtf2":
        transcripts = GTF2_TranscriptAssembler(*streams,
                                               printer=printer,
                                               tabix=tabix,
                                               add_three_for_stop=add_three)
        
    elif args.annotation_format.lower() == "bed":
        transcripts = BED_Reader(*streams,
                                 add_three_for_stop=add_three,
                                 tabix=tabix,
                                 return_type=return_type,printer=printer)

    elif args.annotation_format.lower() == "psl":
        transcripts = PSL_Reader(*streams,
                                 tabix=tabix,
                                 return_type=return_type,printer=printer)
        
    return transcripts

def get_segmentchain_file_parser(input_choices=["BED","BigBed","GTF2","GFF3","PSL"],
                                 disabled=[],
                                 prefix="",
                                 title=_DEFAULT_ANNOTATION_PARSER_TITLE,
                                 description=_DEFAULT_ANNOTATION_PARSER_DESCRIPTION):
    """Convenience method to open annotation files as |SegmentChains|
    
    Parameters
    ----------
    input_choices : list, optional
        list of permitted alignment file type choices
        (Default: ["BED","BigBed","GTF2","GFF3", "PSL"])
        
    disabled : list, optional
        list of parameter names that should be disabled from parser
        without preceding dashes

    prefix : str, optional
        string prefix to add to default argument options (Default: "")
    
    title : str, optional
        title for option group (used in command-line help screen)
        
    description : str, optional
        description of parser (used in command-line help screen)
         
    Returns
    -------
    argparse.ArgumentParser
    
    
    See Also
    --------
    get_segmentchains_from_args
        function that parses the :py:class:`~argparse.Namespace` returned
        by this :py:class:`~argparse.ArgumentParser`
    """
    disabled.append([prefix+"add_three"])
    return get_annotation_file_parser(input_choices=input_choices,
                                      prefix=prefix,
                                      title=title,
                                      disabled=disabled,
                                      description=description)

def get_segmentchains_from_args(args,prefix="",disabled=[],printer=NullWriter()):
    """Return a list of |SegmentChain| objects from arguments parsed by an
    :py:class:`~argparse.ArgumentParser` created by :py:func:`get_segmentchain_file_parser`
    
    Parameters
    ----------
    args : :py:class:`argparse.Namespace`
        Namespace object from :py:func:`get_segmentchain_file_parser`

    prefix : str, optional
        string prefix to add to default argument options.
        Must be same prefix that was added in call to :py:func:`get_segmentchain_file_parser`
        (Default: "")
        
    disabled : list, optional
        list of parameter names that were disabled when the annotation file
        parser was created by :py:func:`get_segmentchain_file_parser`. 
        (Default: ``[]``)
                
    printer : file-like
        A stream to which stderr-like info can be written (default: |NullWriter|) 
    
    
    Returns
    -------
    iterator
        sequence of |SegmentChain| objects, either in order of appearance
        (if input was a BED or PSL file), or sorted lexically by chromosome,
        start coordinate, end coordinate, and then strand (if input was) GTF or GFF
    
    
    See Also
    --------
    get_segmentchain_file_parser
        Function that creates :py:class:`argparse.ArgumentParser` whose output
        :py:class:`~argparse.Namespace` is processed by this function    
    """
    disabled.append([prefix+"add_three"])
    return get_transcripts_from_args(args,
                                     prefix=prefix,
                                     disabled=disabled,
                                     printer=printer,
                                     return_type=SegmentChain)

def get_mask_file_parser(prefix="mask_",disabled=[]):
    """Convenience method to open annotation files that describe regions
    of the genome to mask from analyses
    
    Parameters
    ----------
    prefix : str, optional
        Prefix to add to default argument options (Default: "mask_")
        
    disabled : list, optional
        list of parameter names to disable from the mask file parser 
        (Default: ``[]``, ``add_three`` is always disabled.)

    Returns
    -------
    argparse.ArgumentParser
    
    See Also
    --------
    get_genome_hash_from_mask_args
        function that parses the :py:class:`~argparse.Namespace` returned
        by this :py:class:`~argparse.ArgumentParser`    
    """
    disabled.append(prefix+"add_three")
    return get_segmentchain_file_parser(prefix=prefix,
                                        disabled=disabled,
                                        input_choices=["BED","BigBed","PSL"],
                                        title=_MASK_PARSER_TITLE,
                                        description=_MASK_PARSER_DESCRIPTION)


def get_genome_hash_from_mask_args(args,prefix="mask_",printer=NullWriter()):
    """Return a |GenomeHash| of regions from command-line arguments

    Parameters
    ----------
    args : :py:class:`argparse.Namespace`
        Namespace object from :py:func:`get_mask_file_parser`
    
    prefix : str, optional
        string prefix to add to default argument options.
        Must be same prefix that was added in call to :py:func:`get_mask_file_parser`
        (Default: "mask_")
    
    printer : file-like
        A stream to which stderr-like info can be written (default: |NullWriter|) 


    Returns
    -------
    |GenomeHash|
        Hashed data structure of masked genomic regions
        
    
    See Also
    --------
    get_mask_file_parser
        Function that creates :py:class:`argparse.ArgumentParser` whose output
        :py:class:`~argparse.Namespace` is processed by this function  
    """
    tmp = PrefixNamespaceWrapper(args,prefix)
    if len(tmp.annotation_files) > 0:
        printer.write("Opening mask annotation file(s) %s..." % ", ".join(tmp.annotation_files))
        if len(tmp.annotation_files) > 0:
            if tmp.annotation_format.lower() == "bigbed":
                if len(tmp.annotation_files) > 1:
                    printer.write("Bad arguments: we can only process one BigBed file.")
                    sys.exit(2)
                return BigBedGenomeHash(tmp.annotation_files[0])
            elif tmp.tabix == True:
                return TabixGenomeHash(tmp.annotation_files,tmp.annotation_format,printer=printer)
            else:
                hash_ivcs = get_segmentchains_from_args(args,prefix=prefix,printer=printer)
                return GenomeHash(hash_ivcs)
    else:
        return GenomeHash([])
    

#===============================================================================
# INDEX: Utility classes
#===============================================================================

class PrefixNamespaceWrapper(object):
    """Wrapper class to facilitate processing of :py:class:`~argparse.Namespace`
    objects created by :py:func:`get_alignment_file_parser` or
    :py:func:`get_annotation_file_parser` with non-empty ``prefix`` values,
    as if no prefix had been used.
    
    Attributes
    ----------
    namespace : :py:class:`~argparse.Namespace`
        Result of calling :py:meth:`argparse.ArgumentParser.parse_args`
    
    prefix : str
        Prefix that will be prepended to names of attributes of `self.namespace`
        before they are fetched. Must match prefix that was used in creation
        of the :py:class:`argparse.ArgumentParser` that created `self.namespace`
    
    See Also
    --------
    get_annotation_file_parser
        Creates `:py:class:~argparse.ArgumentParser` for genome annotation files, 
        whose :py:class:`~argparse.Namespace` objects could be wrapped her
    
    get_alignment_file_parser
        Creates `:py:class:~argparse.ArgumentParser` for alignment or count files
        :py:class:`~argparse.Namespace` objects could be wrapped here
    
    get_genome_array_from_args
        Parser function that uses this class internally
    
    get_transcripts_from_args
        Parser function that uses this class internally
    """
    
    def __init__(self,namespace,prefix):
        """Create a |PrefixNamespaceWrapper|
        
        Parameters
        ----------
        namespace : :py:class:`~argparse.Namespace`
            Result of calling :py:meth:`argparse.ArgumentParser.parse_args`
        
        prefix : str
            Prefix that will be prepended to items from the :py:class:`~argparse.Namespace`
            before they are checked 
        """
        self.namespace = namespace
        self.prefix = prefix
    
    def __getattr__(self,k):
        """Fetch an attribute from `self.namespace`, appending `self.prefix` to `k`
        before fetching
        
        Parameters
        ----------
        k : str
            Attribute to fetch
        """
        return getattr(self.namespace,"%s%s" % (self.prefix,k))


#===============================================================================
# INDEX: Utility functions
#===============================================================================


def _parse_variable_offset_file(fh):
    """Read a variable-offset text file into a dictionary.
    These text-files are two-columns and tab-delimited. The first column
    specifies the read length, or contains the special value 'default'. The
    second column specifies the offset from the 5' end of that read length to 
    use.
    
    Parameters
    ----------
    fh : file-like
        open filehandle pointing to data
    
    Returns
    -------
    dict
        dictionary mapping sequencing read lengths to their 5' offsets
    """
    my_dict = {}
    for line in fh:
        items = line.strip("\n").split("\t")
        if len(items) != 2:
            raise MalformedFileError(fh.__name__,"More or fewer than two columns on line:\n\t%s" % line.strip("\n"))
        key   = items[0]
        try:
            key = key if key == "default" else int(key)
        except ValueError:
            raise MalformedFileError(fh.__name__,"Non integer value for key '%s' on line:\n\t%s" % (key,line.strip("\n")))
        if key in my_dict:
            raise MalformedFileError(fh.__name__,"multiple offsets defined for read length %s" % key)
        else:
            try:
                my_dict[key] = int(items[1])
            except ValueError:
                raise MalformedFileError(fh.__name__,"Non integer value for value '%s' on line:\n\t%s" % (items[1],line.strip("\n")))
            
    return my_dict
