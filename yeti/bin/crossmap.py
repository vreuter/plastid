#!/usr/bin/env python
"""Empirically determine which positions in a genome cannot give rise to uniquely-
mapping sequencing reads. These positions are then saved in a :term:`mask file`,
so that they may be excluded as from further analyses.

To identify such positions, a genome sequence is diced into :term:`k-mers <k-mer>`
aligned back to the genome. :term:`k-mers <k-mer>` that align to more than 
one genomic location are then marked as deriving from repetitive regions of
the genome. These regions are exported in a `BED`_ file.

`k` is specified by the user, as are the alignment parameters.


Output files
------------
    ${OUTBASE}_crossmap.bed
        Final :term:`mask file` annotation, in `BED`_ format
    
    ${OUTBASE}_kmers.fa
        :term:`K-mers <k-mer>` derived from genome. This file can be used to make subsequent
        :term:`mask files <mask file>` under different alignment parameters, using the
        the ``--have_kmers`` option


Notes
-----
For large genomes, it is highly recommended to convert the `BED`_-format output
to a `BigBed`_, using Jim Kent's ``bedToBigBed`` utility as follows
(from the terminal)::

    $ bowtie-inspect --summary BOWTIE_INDEX | grep Sequence | cut -f2,3 >OUTFILE.sizes
    $ sort -k1,1 -k2,2n OUTBASE.bed > OUTBASE_sorted.bed
    $ bedToBigBed OUTBASE_sorted.bed OUTBASE.sizes OUTBASE_sorted.bb


For small genomes (e.g. yeast, E. coli), this is unnecessary, and comes at a
cost in speed.

See https://github.com/ENCODE-DCC/kentUtils/tree/master/src/product/scripts
for download & documentation of Kent utilities
"""
__author__ = "joshua"
import argparse
import sys
import os
import subprocess
import re
import inspect
from Bio import SeqIO
from yeti.util.io.filters import NameDateWriter, AbstractReader
from yeti.util.io.openers import get_short_name, argsopener, opener
from yeti.genomics.roitools import SegmentChain, positionlist_to_segments, GenomicSegment
from yeti.util.scriptlib.help_formatters import format_module_docstring
from yeti.util.services.mini2to3 import xrange
namepat = re.compile(r"(.*):([0-9]+)\(\+\)")
printer = NameDateWriter(get_short_name(inspect.stack()[-1][1]))


BigBedMessage = """Crossmap complete and saved as 'OUTFILE.bed'.

    For large (e.g. mammalian) genomes, it is highly recommended to convert
    the BED-format output to a BigBed file, using Jim Kent's bedToBigBed
    utility as follows (from the terminal):
    
        $ bowtie-inspect --summary BOWTIE_INDEX | grep Sequence | cut -f2,3 >OUTFILE.sizes
        $ sort -k1,1 -k2,2n OUTFILE.bed > OUTFILE_sorted.bed
        $ bedToBigBed OUTFILE_sorted.bed OUTFILE.sizes OUTFILE_sorted.bb
    
    
    See https://github.com/ENCODE-DCC/kentUtils/tree/master/src/product/scripts
    for download & documentation of Kent utilities
    
    
"""

def simulate_reads(seq_record,fh=sys.stdout,k=30):
    """Chops a DNA sequence into :term:`k-mers <k-mer>`, mimicking a sequencing run.
    Output is delivered in fasta format. Sequences are named for position of
    origin using 0-based indices.
    
    Parameters
    ----------
    seq_record : :py:class:`Bio.SeqRecord.SeqRecord`
        DNA sequence
    
    fh : file-like
        filehandle to write output 
        
    k : int, optional
        length of k-mers to generate (Default: 30)
    """
    for x in xrange(0,len(seq_record)-k+1):
        fh.write(">%s:%s(+)\n" % (seq_record.name,x))
        fh.write("%s\n" % str(seq_record.seq)[x:x+k])

    return None

class FastaNameReader(AbstractReader):
    """Returns names of sequences in a fasta file"""

    def filter(self,line):
        """Return next sequence name in a fasta file

        Parameters
        ----------
        line : str
            Line of text

        Returns
        -------
        str
            Name of next sequence, excluding prefix ">" and line terminator
        """
        if line.startswith(">"):
            return line[1:].rstrip()
        else:
            return self.__next__()

def revcomp_mask_ivc(seg,k,offset=0):
    """Reverse-complement a single-interval mask, correcting for `offset`.
    
    Parameters
    ----------
    seg : |SegmentChain|
        Plus-strand mask, including `offset`

    k : int
        Length of k-mers

    offset : int, optional
        Offset from 5\' end of read at which to map mask (Default: 0)

    Returns
    -------
    |SegmentChain|
        Mask on minus strand corresponding to ``seg``
    """
# Algorithm note:
#
#     Let
#         FW = plus-strand coordinate
#         RC = minus-strand coordinate
#     
#     Then
#         RC = FW + k - 1 - offset
#     
#     But we are given FW + offset, so:
#     
#         RC + offset = (FW + offset) + k - 1 - offset
#         RC = (FW + offset) + k - 1 - 2*offset    
    ivminus = GenomicSegment(seg.spanning_segment.chrom,
                             seg.spanning_segment.start + k - 1 - 2*offset,
                             seg.spanning_segment.end + k - 1 - 2*offset,
                             "-")
    return SegmentChain(ivminus)

def fa_to_bed(toomany_fh,k,offset=0):
    """Create a `BED`_ file indicating genomic origins of reads in a `bowtie`_ ``toomany`` file
    
    Parameters
    ----------
    toomany_fh : file-like
        Open filehandle to fasta-formatted ``toomany`` file from `bowtie`_

    k : int
        Length of k-mers

    offset : int, optional
        Offset from 5\' end of read at which to map read, if any (Default: 0)

    Yields
    ------
    |SegmentChain|
        Plus-strand |SegmentChain| representing a repetitive region

    |SegmentChain|
        Minus-strand |SegmentChain| representing a repetitive region
    """
    last_chrom = None
    last_pos   = None
    start_pos  = None
    reader = FastaNameReader(toomany_fh)

    for read_name in reader:
        chrom,pos = namepat.search(read_name).groups()
        pos = int(pos) + offset
        if chrom != last_chrom:
            if last_chrom is not None:
                my_range = set(range(start_pos,last_pos+1))
                plus_ivc  = SegmentChain(*positionlist_to_segments(last_chrom,"+",my_range))
                minus_ivc = revcomp_mask_ivc(plus_ivc,k,offset)
                last_chrom = chrom
                start_pos  = pos
                last_pos   = pos
                yield plus_ivc, minus_ivc
            else:
                last_chrom = chrom
                start_pos  = pos
                last_pos   = pos
        else:
            delta = pos - last_pos
            if delta > 1:
                my_range = set(range(start_pos,last_pos+1))
                last_pos   = pos
                start_pos  = pos
                plus_ivc  = SegmentChain(*positionlist_to_segments(chrom,"+",my_range))
                minus_ivc = revcomp_mask_ivc(plus_ivc,k,offset)
                yield plus_ivc, minus_ivc
            elif delta == 1:
                last_pos = pos
            else: # delta < 0:
                raise AssertionError("K-mers are not sorted at read %s! Aborting." % read_name)
    
    # export final feature
    my_range = set(range(start_pos,last_pos+1))
    plus_ivc  = SegmentChain(*positionlist_to_segments(chrom,"+",my_range))
    minus_ivc = revcomp_mask_ivc(plus_ivc,k,offset)
    yield plus_ivc, minus_ivc

def main(argv=sys.argv[1:]):
    """Command-line program
    
    Parameters
    ----------
	argv : list, optional
		A list of command-line arguments, which will be processed
		as if the script were called from the command line if
		:py:func:`main` is called directly.

        Default: `sys.argv[1:]`. The command-line arguments, if the script is
        invoked from the command line
    """
    parser = argparse.ArgumentParser(description=format_module_docstring(__doc__),
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-k",dest="read_length",metavar="READ_LENGTH",
                        type=int,default=29,
                        help="K-mer length to generate from input file. "+
                             "(Default: 29)")
    parser.add_argument("--offset",type=int,default=14,
                        help="Offset from 5\' end of plus-strand read at which to attribute score (Default: 14)")
    parser.add_argument("--mismatches",metavar="N",
                        type=int,default=0,
                        help="Number of mismatches tolerated in alignment. "+
                           "(Default: 0)")
    parser.add_argument("-f","--seqfile_format",dest="seqfile_format",default="fasta",
                        choices=("fasta","genbank","embl"),
                        help="Format of input file (fasta, genbank, embl; Default: fasta)")
    parser.add_argument("--bowtie",dest="bowtie",default="/usr/local/bin/bowtie",
                        type=str,
                        help="Location of bowtie binary (Default: ``/usr/local/bin/bowtie``)")
    parser.add_argument("--have_kmers",default=False,action="store_true",
                        help="seqfile contains k-mers from a previous `crossmap` run, instead of a genome sequence to be diced.")
    parser.add_argument("seqfile",type=str,
                        help="Sequences of chromosomes or contigs (not transcripts) that will be crossmapped, or, a file of k-mers from a previous run of `crossmap` (if ``--have_kmers`` is specified)")
    parser.add_argument("ebwt",type=str,
                        help="Bowtie index of genome against which crossmap will be made. In most cases, should be generated from the same sequences that are in `seqfile`.")
    parser.add_argument("outbase",type=str,
                        help="Basename for output files")
    args = parser.parse_args(argv)


    #filenames
    base         = "%s_%s_%s" % (args.outbase, args.read_length, args.mismatches)
    kmer_file    = "%s_kmers.fa"     % base
    toomany_file = "%s_multimap.fa"  % base
    bed_file     = "%s_crossmap.bed" % base

    if not os.path.exists(args.seqfile):
        printer.write("Could not find source file: %s" % args.seqfile)
        printer.write("Exiting.")
        sys.exit(1)
    
    #simulate reads if necessary
    if args.have_kmers == False:
        printer.write("Dicing sequence file '%s' into '%s'" % (args.seqfile, kmer_file))
        seq_file  = opener(args.seqfile,"r")
        kmer      = opener(kmer_file,"w") 
        seqs      = SeqIO.parse(seq_file,args.seqfile_format)
        for seq in seqs:
            printer("Processing %s" % seq.name)
            simulate_reads(seq,kmer,args.read_length)
    else:
        printer.write("Using kmers from file '%s'" % (args.seqfile))
        kmer_file = args.seqfile
            
    #map reads using bowtie
    printer.write("Discarding uniquely mapping reads via alignment")
    
    argdict = { "mismatches" : args.mismatches,
                "processors" : 1, 
                "bowtie"     : args.bowtie,
                "toomany"    : toomany_file,
                "kmers"      : kmer_file,
                "ebwt"       : args.ebwt,
                "null"       : os.devnull,
                }
    
    cmd  = "%(bowtie)s -m1 -a --best -f -v %(mismatches)s -p %(processors)s %(ebwt)s %(kmers)s --max %(toomany)s >%(null)s" % argdict

    printer.write("Executing:\n\t'%s'" % cmd)
    try:
        retcode = subprocess.call(cmd,shell=True)
        if retcode < 0 or retcode == 2:
            printer.write("Alignment terminated with status %s" % retcode)
        else:
            if os.path.exists(toomany_file):
                printer.write("Assembling multimappers into crossmap...")
                with argsopener(bed_file,args,"w") as bed_out:
                    for plus_ivc, minus_ivc in fa_to_bed(open(toomany_file),
                                                         args.read_length,
                                                         offset=args.offset):
                        bed_out.write(plus_ivc.as_bed())
                        bed_out.write(minus_ivc.as_bed())
                
                    bed_out.close()
            
            else:
                printer.write("Could not find multimapper source file '%s' ." % toomany_file)
                sys.exit(2)
    except OSError as e:
        printer.write("Alignment failed: %s" % e)
        sys.exit(2)

    printer.write("Cleaning up...")
    os.remove(toomany_file)
    
    printer.write("Done.")
    printer.write(BigBedMessage.replace("OUTFILE",bed_file.replace(".bed","")).replace("BOWTIE_INDEX",args.ebwt))


if __name__ == "__main__":
    main()
