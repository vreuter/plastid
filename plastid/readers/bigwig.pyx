"""Fast reader for `BigWig`_ files, implemented as a Python binding for the C
library of Jim Kent's utilties for the UCSC genome browser.


See also
--------
`Kent2010 <http://dx.doi.org/10.1093/bioinformatics/btq351>`_
    Description of BigBed and BigWig formats. Especially see supplemental data.

`Source repository for Kent utilities <https://github.com/ENCODE-DCC/kentUtils.git>`_
    The header files are particularly useful.
"""
import warnings
cimport numpy
import numpy

from plastid.util.services.exceptions import DataWarning
from plastid.genomics.roitools cimport GenomicSegment, SegmentChain
from plastid.genomics.c_common cimport reverse_strand
from plastid.readers.bbifile cimport _BBI_Reader, bbiInterval,\
                                     bigWigFileOpen,\
                                     close_file,\
                                     bigWigValsOnChrom, bigWigIntervalQuery,\
                                     bigWigValsOnChromNew, bigWigValsOnChromFree,\
                                     bigWigValsOnChromFetchData,\
                                     lmInit, lmCleanup, lmAlloc, lm

from plastid.readers.bbifile cimport WARN_CHROM_NOT_FOUND



cdef class BigWigReader(_BBI_Reader):
    """Reader providing random or sequential access to data stored in `BigWig`_ files.
    """

    def __cinit__(self,str filename, double fill = numpy.nan):
        """Open a `BigWig`_ file.
        
        Parameters
        ----------
        filename : str
            Name of `bigwig`_ file
            
        fill : float
            Value to use when there is no data covering a base (e.g. zero, nan,
            et c. Default: `numpy.nan`)
        """
        # pointer to file; opened here but closed in __dealloc__ of _BBI_Reader
        self._bbifile = bigWigFileOpen(bytes(filename))
        
        # value for empty/missing data
        self.fill = fill
        
        # local memory buffer
        self._lm = NULL
        
    def __dealloc__(self):
        """Deallocate memory buffer ``self._lm``, if allocated"""
        if self._lm != NULL:
            lmCleanup(&self._lm)
  
    cdef lm * _get_lm(self):
        """Return ``self._lm``, allocating it if necessary
        
        Returns
        -------
        lm
            local memory buffer
            
        Raises
        ------
        MemoryError
            If memory cannot be allocated
        """
        if self._lm == NULL:
            self._lm = lmInit(0)

        if not self._lm:
            raise MemoryError("BigWig.__get__: Could not allocate memory.")
            
        return self._lm
         
    def __getitem__(self,roi): #,roi_order=True): 
        """Retrieve array of counts from a region of interest, following
        the mapping rule set by :meth:`~BAMGenomeArray.set_mapping`.
        Values in the vector are ordered 5' to 3' relative to `roi`
        rather than the genome (i.e. are reversed for reverse-strand
        features).
        
        Parameters
        ----------
        roi : |GenomicSegment| or |SegmentChain|
            Region of interest in genome
        
        roi_order : bool, optional
            If `True` (default) return vector of values 5' to 3' 
            relative to vector rather than genome.

        Returns
        -------
        numpy.ndarray
            vector of numbers, each position corresponding to a position
            in `roi`, from 5' to 3' relative to `roi`
        
        See also
        --------
        plastid.genomics.roitools.SegmentChain.get_counts
            Fetch a spliced vector of data covering a |SegmentChain|
        """
        cdef:
            long start    = roi.start
            long end      = roi.end
            str chrom     = roi.chrom
            size_t length = end - start
            
            numpy.ndarray counts = numpy.full(length,self.fill,dtype=numpy.float)
            double [:] view      = counts
            
            lm* buf = self._get_lm()
            bbiInterval* iv
            long segstart, segend
                    
        # return empty vector if chromosome is not in BigWig file
        if chrom not in self.c_chroms():
            warnings.warn(WARN_CHROM_NOT_FOUND % (chrom,self.filename),DataWarning)
            return counts
        
        # populate vector
        iv = bigWigIntervalQuery(self._bbifile,bytes(chrom),start,end,buf)
        while iv is not NULL:
            segstart = iv.start - start
            segend = iv.end - start
            view[segstart:segend] = iv.val
            iv = iv.next

#         if roi_order == True and roi.c_strand == reverse_strand:
#             counts = counts[::-1]

        return counts

    def get_chromosome(self,str chrom):
        """Retrieve values across an entire chromosome more efficiently than using `self[chromosome_segment]`
        
        Parameters
        ----------
        chrom : str
            Chromosome name
            
        Returns
        -------
        numpy.ndarray
            Numpy array of floats
        """
        cdef:
            lm* buf = self._get_lm()
            bigWigValsOnChrom* vals
            long length
            long i = 0
            numpy.ndarray counts, mask
            bint success
            
            
        #     cdef struct bigWigValsOnChrom:
        #         bigWigValsOnChrom *next
        #         char   *chrom
        #         long   chromSize
        #         long   bufSize     # size of allocated buffer
        #         double *valBuf     # value for each base on chrom. Zero where no data
        #         Bits   *covBuf     # a bit for each base with data
        vals    = bigWigValsOnChromNew()
        success = bigWigValsOnChromFetchData(vals,bytes(chrom),self._bbifile)
        length  = vals.chromSize

        if chrom not in self.c_chroms():
            warnings.warn(WARN_CHROM_NOT_FOUND % (chrom,self.filename),DataWarning)
            counts = numpy.full(length,self.fill)
        elif success == False:
            warnings.warn("Could not retrieve data for chrom '%s' from file '%s'." % (chrom,self.filename),DataWarning)
            counts = numpy.full(length,self.fill)
        else:
            counts = numpy.asarray(<numpy.double_t[:length]> vals.valBuf)
            
            # if fill isn't 0, set no-data values in output to self.fill
            # these are in vals.covBuf
            #
            # Bits is typedefed as unsigned char in kentUtils/inc/bits.h
            # That corresponds to a 1 byte unsigned int in numpy
            if self.fill != 0:
                mask = numpy.asarray(<numpy.uint8_t[:length]> vals.covBuf)
                counts[mask == 0] = self.fill

        bigWigValsOnChromFree(&vals)
        return counts
            
    def __iter__(self):
        return iter(self)
    
    def __next__(self):
        """Iterate over values in the `BigWig`_ file, sorted lexically by position.
        
        Yields
        ------
        tuple
            `(chrom name, start, end, value)`, where start & end are 0-indexed
            and half-open
        """
        cdef:
            list chroms = sorted(self.c_chroms().keys())
            str chrom
            long start, end
            double val
            lm* buf = self._get_lm()
        
        for chrom in chroms:
            #bigWigValsOnChrom
            pass

    def next(self):
        """Iterate over values in the `BigWig`_ file, sorted lexically by position.
        
        Yields
        ------
        tuple
            `(chrom name, start, end, value)`, where start & end are 0-indexed
            and half-open
        """
        return next(self)

