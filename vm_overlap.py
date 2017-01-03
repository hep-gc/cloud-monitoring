#!/bin/env python

# -----------------------------------------------------------------------
# Determine the time overlap of the VM with the measurement window
#
# Aug 31 2016
# -----------------------------------------------------------------------
#
# type 1 (no overlap before or after)
#      |---VM---|
#                   |---Win---|
#
# type 2
#      |---VM---|
#           |---Win---|
#
# type 3
#         |---VM---|
#      |-----Win-----|
#
# type 4
#            |---VM---|
#      |---Win---|
#
# type 5
#    |------VM-----|
#      |---Win---|
#
# input:
# (v1, v2) = (start,end) times of VM
# (w1, w2) = (start,end) times of measurement window
#
# output:
# otype = type of the VM overlap with the measurement window (0 = no overlap)
# fraction = fraction of the VM lifetime in the measurement window
# -----------------------------------------------------------------------

def overlap_test( v1, v2, w1, w2):
    print 'overlap_test: v1,v2 = ', v1, v2
    print 'overlap_test: w1,w2 = ', w1, w2



def overlap( v1, v2, w1, w2):

# initial return values
    otype = 0
    fraction = float(0)

# check values make sense (v2>v1>0) and within last year
    if v1 < 0 or v2 < 0 or w1 < 0 or w2 < 0:
       print 'overlap:  invalid input (v1,v2,w1,w2) = ', v1,v2,w1,w2
       return otype, fraction

    vmdiff = float(v2) - float(v1)
    if vmdiff < 0:
       print 'overlap: v2-v1 < 0  value = ', vmdiff
       return otype, fraction

    if w2-w1 < 0:
       print 'overlap: w2-w1 < 0  value = ', w2-w1
       return otype, fraction

# determine type of overlap of VM lifetime with measurement window
    otype = 0
    fraction = float(0)

# type 1
    if  v2 < w1 or v1 > w2:
        otype = 1
        return otype, fraction

# type 2
    if v1 < w1 and v2 > w1 and v2 < w2:
       otype = 2
       fraction = (v2 - w1)/vmdiff
       return otype, fraction

# type 3
    if v1 > w1 and v1 < w2 and v2 > w1 and v2 < w2:
       otype = 3
       fraction = 1
       return otype, fraction

# type 4
    if v1 > w1 and v1 < w2 and v2 > w2:
       otype = 4
       fraction = (w2 - v1)/vmdiff
       return otype, fraction

# type 5
    if v1 < w1 and v2 > w2:
       otype = 5
       fraction = (w2 - w1)/vmdiff
       return otype, fraction

# unknown type
    if otype == 0:
       print 'overlap: otype = 0 problem'
    
    return otype, fraction
