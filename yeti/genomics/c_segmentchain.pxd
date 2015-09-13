from yeti.genomics.c_roitools cimport GenomicSegment, Strand
from yeti.genomics.c_common cimport ExBool, bool_exception

cdef class SegmentChain(object):
    cdef:
        long length
        Strand c_strand
        list _segments, _mask_segments
        GenomicSegment spanning_segment
        long [::1] _position_hash
        int  [::1] _position_mask # really should be bint, but we can't use it there
        dict attr, _inverse_hash

    cdef void _update(self)
    cpdef void sort(self)
    #cpdef list shares_segments_with(self,object)
#    cpdef bint unstranded_overlaps(self,object)
#    cpdef bint overlaps(self,object) except? False
#    cpdef bint antisense_overlaps(self,object)
#    cpdef bint covers(self,object)
    cdef  list c_shares_segments_with(self,SegmentChain)
    cdef  ExBool c_covers(self,SegmentChain) except bool_exception
    cdef  ExBool c_unstranded_overlaps(self,SegmentChain) except bool_exception 
    cdef  ExBool c_overlaps(self,SegmentChain) except bool_exception
    cdef  ExBool c_antisense_overlaps(self,SegmentChain) except bool_exception
    cdef  ExBool c_contains(self,SegmentChain) except bool_exception
    cdef  ExBool c_richcmp(self,SegmentChain,int) except bool_exception
    cpdef SegmentChain get_antisense(self)
    cpdef list get_position_list(self)
    cpdef set get_position_set(self)
    cdef long [::1] _update_position_hash(self)
    cdef dict _update_inverse_hash(self)
    cpdef long get_length(self)
    cdef long c_get_genomic_coordinate(self,long,bint) except -1
    cdef long c_get_segmentchain_coordinate(self,long,bint) except -1
    cdef SegmentChain c_get_subchain(self,long,long,bint)


cdef class Transcript(SegmentChain):
    cdef void _update(self)

