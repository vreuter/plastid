Glossary of terms
=================

.. glossary ::
   :sorted:


   0-indexed
   0-indexed coordinates
      In :term:`0-indexed` coordinate systems, the first position or coordinate
      is labeled `0`. :term:`0-indexed coordinates` are typical in Python, 
      where all slicing and indexing of lists, strings, and all other sliceable
      objects occurs in :term:`0-indexed` and :term:`half-open` coordinate
      representation.
      
      In contrast, see :term:`1-indexed coordinates`. For a detailed discussion
      with examples, see :doc:`/concepts/coordinates`.

   1-indexed
   1-indexed coordinates
      In :term:`1-indexed` coordinate systems, the first position or coordinate
      is labeled `1`. In contrast, see :term:`0-indexed coordinates`. For
      a detailed discussion with examples, see :doc:`/concepts/coordinates`.

   half-open
      In :term:`half-open` coordinate systems, the end coordinate of a
      :term:`feature` is defined as the first position **NOT** included in
      the feature. So, in this representation, the end coordinate of a
      3-nucleotide :term:`feature` that starts at position 3 would be 6.
       
       :term:`half-open` coordinates are typical in Python,
      where all slicing and indexing of lists, strings, or other sliceable
      objects use :term:`0-indexed` and :term:`half-open` coordinate representation.

      In contrast, see :term:`fully-closed` coordinates. For a detailed discussion
      with examples, see :doc:`/concepts/coordinates`.
   
   fully-closed
   end-inclusive
      In :term:`fully-closed` coordinate systems, the end coordinate of a
      :term:`feature` is defined as the last position included in the feature.
      So, in this representation, the end coordinate of a 3-nucleotide
      :term:`feature` that starts at position 3 would be 5.

      In contrast, see :term:`half-open` coordinates. For a detailed discussion,
      with examples, see :doc:`/concepts/coordinates`.

   alignment
   read alignments
      A record matching a short sequence of DNA or RNA to a region of identical or similar
      sequence in a genome. In a :term:`high-throughput sequencing` experiment,
      alignment of short reads identifies the genomic coordinates from which
      each read presumably derived.
       
      These are produced by running sequencing
      data through alignment programs, such as `Bowtie`_, `Tophat`_, or `BWA`_.
      The most common format for short read alignments is `BAM`_.

   annotation
      A file that describes locations and properties of :term:`features <feature>`
      (e.g. genes, mRNAs, SNPs, start codons) in a genome. Annotation files
      come in various formats, such as `BED`_, `BigBed`_, `GTF2`_, `GFF3`_,
      and `PSL`_, among others. In a :term:`high-throughput sequencing`
      experiment, it is essential to make sure that the coordinates in the
      :term:`annotation` correspond to the :term:`genome build` used
      to generate the alignments.

   counts
      Colloquially, the number of :term:`read alignments` overlapping a region
      of interest, or mapped to a nucleotide.
  
   count file
      A file that assigns quantitative data -- for example, read alignment
      counts, or conservation scores -- to genomic coordinates. Strictly
      speaking, these include  `bedGraph`_ or `wiggle`_ files but :py:obj:`plastid`
      can also treat :term:`alignment` files in `bowtie`_ or `BAM`_ format
      as count files, if a :term:`mapping rule` is applied.

   DMS-seq
      An RNA structure probing technique using :term:`high-throughput sequencing`.
      See :cite:`Rouskin2014` for details.

   crossmap
      A :term:`mask file` that annotates regions of the genome that give rise to
      multimapping reads under given alignment criteria. Crossmaps may be made
      using the |crossmap| script
   
   indexed file format
      A file that indexes its own data, enabling readers to selectively load
      only the portions of data that are needed. This substantially saves
      memory. Indexed data formats include `BAM`_, `BigWig`_, `BigBed`_ and
      `tabix`_-compressed `GTF2`_, `GFF3`_, and `BED`_ files. 
      See :ref:`concepts-data-formats` for further discussion.  
   
   mask file
   mask annotation file
      An :term:`annotation` file that identifies regions of the genome to
      exclude from analysis, such as repetitive regions.
      
      See :doc:`/examples/using_masks` for information on creating and using
      mask files.

   factory function
      A function that produces functions

   feature
      A region of the genome with interesting or specific properties, such
      as a gene, an mRNA, an exon, a centromere, et c.

   genome assembly
   genome build
      A specific edition of a genome sequence for a given organism. These
      are updated over time as sequence data is added and/or corrected.
      When an assembly is updated, frequently the lengths of the chromosomes or
      contigs change as sequences are corrected. 

   genome browser
      Software used for visualizing genomic sequence, :term:`feature`
      annotations, :term:`read alignments`, and other quantitative data
      (e.g. nucleotide-wise sequence conservation). Popular genome browsers
      include `IGV`_ and the `UCSC genome browser`_. 

   deep sequencing
   high-throughput sequencing
      A group of experimental techniques that produce as output millions of
      reads (strings) of short DNA sequences.

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

      See :doc:`/concepts/mapping_rules` for an in-depth discusion, with examples.

   maximal spanning window
      The largest possible window over which a group of regions (for example,
      transcripts) share corresponding genomic positions.
      
      For example,
      if a gene has a single start codon, the :term:`maximal spanning window`
      surrounding that start codon can be made by growing a window along the
      transcripts in the 5' and 3' directions, starting at the start codon,
      and stopping in each direction as soon as the next coordinate no longer
      corresponds to the same genomic position in all transcripts:
      
      .. figure:: /_static/images/metagene_maximal_spanning_window.png
         :alt: Metagene - maximal spanning window
         :figclass: captionfigure
         
         :term:`Maximal spanning window` surrounding a start codon over 
         a family of transcripts.
       
      :term:`Maximal spanning windows <maximal spanning window>` are often
      used in :term:`metagene` analyses. 

   metagene
   metagene average
      An average of quantitative data over one or more
      genomic regions (often genes or transcripts) aligned at some internal feature.
      For example, a :term:`metagene` profile could be built around:
    
       - the average of ribosome density surrounding the start codons of all 
         transcripts in a :term:`ribosome profiling` dataset
      
       - an average phylogenetic conservation score surounding the 5' splice
         site of the first introns of all transcripts
    
      See :doc:`/examples/metagene` and/or the module documentation for the
      :py:mod:`~plastid.bin.metagene` script for more explanation.

   multimap
   multimapping
      A read that aligns equally well (or nearly-equally well) to multiple
      regions in a genome or transcriptome is said to be :term:`multimapping`
      in that genome or transcriptome.
      
      :term:`Multimapping` reads arise from repeated sequence, for example
      from duplicated genes, transposons, telomeres, tandem repeats, or
      segmental duplications within genes. 

   footprint
   ribosome-protected footprint
      A fragment of mRNA protected from nuclease digestion by a ribosome
      during ribosome profiling or other molecular biology assays.

   ribosome profiling
      A :term:`high-throughput sequencing` technique that captures the positions
      of all ribosomes on all RNAs at a snapshot in time. See :cite:`Ingolia2009`
      for more details

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
      
      .. figure:: /_static/images/p_site_map_cartoon.png
         :alt: Cartoon of ribosomal P-site
         :width: 30ex
         :align: center
         :figclass: captionfigure
        
         Ribosome, :term:`footprint`, and P-site offset. After :cite:`Ingolia2009`.
          
      Because the P-site is the site where peptidyl elongation occurs,
      :term:`read alignments` from :term:`ribosome profiling` are frequently
      mapped to their P-sites, so that translation may be visualized
      along a transcript.
      
      P-site offsets may be estimated from ribosome profiling data
      using the :py:mod:`~plastid.bin.psite` script. For a detailed discussion,
      see :doc:`/examples/p_site`.

   start codon peak
      Large peaks of :term:`ribosome-protected footprint` visible over initiator codons
      in ribosome profiling data. These arise because the kinetics of
      translation initiation are slow compared to the kinetics of
      elongation, causing a build-up over the initiator codon.

   stop codon peak
      Large peaks of :term:`ribosome-protected footprint` visible
      over stop codons in some ribosome profiling datasets. These
      arise because the kinetics of translation termination are 
      slow compared to the kinetics of elongation, causing a build-up
      over termination codons. These peaks are frequently absent
      from datasets if tissues are pre-treated with elongation
      inhibitors (e.g. cycloheximide) before lysis and sample prep.

   sub-codon phasing
   triplet periodicity
      A feature of :term:`ribosome profiling` data. Because ribosomes
      step three nucleotides in each cycle of translation elongation,
      in many :term:`ribosome profiling` datasets a triplet periodicity
      is observable in the distribution of
      :term:`ribosome-protected footprints <footprint>`, in which 70-90%
      of the reads on a codon fall within the first of the three codon
      positions. This allows deduction of translation reading frames,
      if the reading frame is not known *a priori.* See :cite:`Ingolia2009`
      for more details

   translation efficiency
      An mRNA's translation efficiency measures how much protein is
      made from that individual transcript. Translation efficiency
      for an mRNA is therefore proportional to its translation initiation
      rate.

   FDR
   false discovery rate
      The :term:`false discovery rate` is defined as the fraction 
      of positive results that are false positives (:cite:`Benjamini1995`):

      .. math::

         FDR = \frac{FP}{FP + TP}

      For example, at a 5% :term:`false discovery rate`, a set of
      20 positive results would contain approximately 1 false positive.

   Extended BED
   BED X+Y
      Extended `BED`_ files contain 3-12 columns of `BED`_-formatted data (x),
      plus additional (y) tab-delimited columns of arbitrary data.         
      The `ENCODE`_ project has created several such formats (for a complete
      list, see the `UCSC file format FAQ`_), including:

       - `Broad peak <https://genome.ucsc.edu/FAQ/FAQformat.html#format13>`_ (BED 6+3)
       - `Narrow peak <https://genome.ucsc.edu/FAQ/FAQformat.html#format12>`_ (BED 6+4)
       - `tagAlign <https://genome.ucsc.edu/FAQ/FAQformat.html#format15>`_  (BED 3+3)

      :data:`plastid` supports reading BED X+Y formats via the `extra_columns` keyword that can be
      passed to :class:`~plastid.readers.bed.BED_Reader`, or the
      :meth:`~plastid.genomics.roitools.SegmentChain.from_bed` method of |SegmentChain|
      and |Transcript|. It also supports writing BED 12+Y formats via the same keyword
      passed to the :meth:`~plastid.genomics.roitools.SegmentChain.as_bed`.

