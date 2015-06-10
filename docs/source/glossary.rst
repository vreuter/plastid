Glossary of terms
=================

 .. glossary ::
    :sorted:

    alignment
    read alignments
        A record matching a sequencing read to the genomic coordinates from
        which it presumably derived. These are produced by running sequencing
        data through alignment programs, such as `Bowtie`_, `Tophat`_, or `BWA`_.
        The most common format for short read alignments is `BAM`_.

    annotation
        A file that describes locations of features (e.g. genes, mRNAs)
        in a genome. These come in various formats, e.g.  `BED`_, `BigBed`_,
        `GTF2`_, `GFF3`_, and `PSL`_, among others.

    counts
        Colloquially, the number of :term:`read alignments` overlapping a region
        of interest, or mapped to a nucleotide.
    
    count file
        A file that assigns quantitative data -- for example, read alignment
        counts, or conservation scores -- to genomic coordinates. Strictly
        speaking, these include  `bedGraph`_ or `wiggle`_ files but :py:obj:`yeti`
        can also treat :term:`alignment` files in `bowtie`_ or `BAM`_ format
        as count files, if a :term:`mapping rule` is applied.

    crossmap
    mask file
    mask annotation file
        A genomic annotation that identifies regions of the genome that
        cannot give rise to uniquely-mapping reads due to repetitive sequence.
        Crossmaps are functions of genome sequence, read length, and alignment
        parameters (e.g. the number of mismatches allowed). These may be
        generated from genome sequence using the included
        :py:mod:`~yeti.bin.crossmap` script.

    factory function
        A function that produces functions

    feature
        A region of the genome with interesting or specific properties, such
        as a gene, an mRNA, an exon, a centromere, et c.

    genome browser
        Software used for visualizing genomic sequence, :term:`feature`
        annotations, :term:`read alignments`, and other quantitative data
        (e.g. nucleotide-wise sequence conservation). Popular genome browsers
        include `IGV`_ and the `UCSC genome browser`_. 

    k-mer
        A sequence *k* nucleotides long.

    mapping rule
    mapping function
        A function that describes how a read alignment is mapped
        to the genome for positional analyses. Reads typically are mapped
        to their fiveprime or threeprime ends, with an offset of 0 or more
        nucleotides that can optionally depend on the read length.
        
        For example, ribosome-protected mRNA fragments are frequently mapped
        to their :term:`P-site offset` by using a 15 nucleotide offset 
        from the threeprime end of the fragment.

    metagene
    metagene average
        An average of some sort of quantitative information over genes aligned at some
        internal feature. For example, an average of ribosome density across
        all genes, aligned at their start codons. Or, perhaps, an average
        across all genes of nucleotide sequence conservation across the 12
        fly genomes surrounding 5' splice sites of first introns. See the
        documentation for the :py:mod:`~yeti.bin.metagene` script for more
        explanation.

    footprint
    ribosome-protected footprint
        A fragment of mRNA protected from nuclease digestion by a ribosome
        during ribosome profiling or other molecular biology assays.

    roi
    region of interest
        A region of the genome or of a transcript that contains an interesting
        :term:`feature`.

    RPKM
        Reads per kilobase per million reads in a dataset. This is a unit of
        sequencing density that is normalized by sequencing depth (in millions of
        reads) and by the length of the region of interest (in kb).

    single-end sequencing
        A high-throughput sequencing technique that generates short reads
        of approximately 50-100 nt in length.

    paired-end sequencing
        A high-throughput sequencing technique in which 50-100 nucleotides
        of each end of a ~300 nucleotide sequence are read, and reported
        as a pair.

    P-site offset
        Distance from the 5' or 3' end of a ribosome-protected footprint
        to the P-site of the ribosome that generated the footprint.
        P-site offsets may be estimated from ribosome profiling data
        using the :py:mod:`~yeti.bin.psite` script.

    Start codon peak
        Large peaks of :term:`ribosome-protected footprint` visible over initiator codons
        in ribosome profiling data. These arise because the kinetics of
        translation initiation are slow compared to the kinetics of
        elongation, causing a build-up over the initiator codon.

    Stop codon peak
        Large peaks of :term:`ribosome-protected footprint` visible
        over stop codons in some ribosome profiling datasets. These
        arise because the kinetics of translation termination are 
        slow compared to the kinetics of elongation, causing a build-up
        over termination codons. These peaks are frequently absent
        from datasets if tissues are pre-treated with elongation
        inhibitors (e.g. cycloheximide) before lysis and sample prep.
