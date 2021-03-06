#!/usr/bin/python

# Moderately dumb script to generate the Glk library tables for Unicode
# case-mapping.
#
# python casemap.py /path/to/unicode/directory > cgunigen.c
#
# The argument should be a directory which contains UnicodeData.txt
# and SpecialCasing.txt. These files can be found at
# <http://www.unicode.org/Public/UNIDATA/>.

import sys
import os
import string

if (len(sys.argv) < 2):
    print 'Usage: casemap.py /path/to/unicode/directory'
    sys.exit(1)

unicode_dir = sys.argv[1]

try:
    ucdfl = open(os.path.join(unicode_dir, 'UnicodeData.txt'))
    specfl = open(os.path.join(unicode_dir, 'SpecialCasing.txt'))
except IOError:
    print unicode_dir, 'must contain the files UnicodeData.txt and SpecialCasing.txt.'
    sys.exit(1)

# parse UnicodeData.txt

casetable = {}
totalchars = 0
titleablechars = 0
totalspecialcases = 0

blocktable = {}
specialtable = {}

while 1:
    ln = ucdfl.readline()
    if (not ln):
        break
    ln = ln.strip()
    pos = ln.find('#')
    if (pos >= 0):
        ln = ln[ : pos]

    ls = ln.split(';')
    if ((not ls) or (not ls[0])):
        continue

    val = int(ls[0], 16)
    totalchars = totalchars+1

    upcase = val
    downcase = val
    titlecase = val

    if (len(ls) > 12 and ls[12]):
        upcase = int(ls[12], 16)
    if (len(ls) > 13 and ls[13]):
        downcase = int(ls[13], 16)
    if (len(ls) > 14 and ls[14]):
        titlecase = int(ls[14], 16)

    if (val == upcase and val == downcase and val == titlecase):
        continue

    if (upcase != titlecase):
        titleablechars = titleablechars+1
        specialtable[val] = ([upcase], [downcase], [titlecase])
        
    casetable[val] = (upcase, downcase, titlecase)

while 1:
    ln = specfl.readline()
    if (not ln):
        break
    ln = ln.strip()
    pos = ln.find('#')
    if (pos >= 0):
        ln = ln[ : pos]

    ls = ln.split(';')
    ls = [st.strip() for st in ls]
    if ((not ls) or (not ls[0])):
        continue

    val = int(ls[0], 16)

    if (len(ls) > 4 and ls[4]):
        # conditional case, ignore
        continue
        
    totalspecialcases = totalspecialcases+1
    
    speccase = (
        [ int(st, 16) for st in ls[3].split(' ') ],  # upper
        [ int(st, 16) for st in ls[1].split(' ') ],  # lower
        [ int(st, 16) for st in ls[2].split(' ') ]   # title
    )

    casetable[val] = (val, val, val) # placeholder
    specialtable[val] = speccase

sys.stderr.write(str(totalchars) + ' characters in the Unicode database\n')
sys.stderr.write(str(len(casetable)) + ' characters which can change case\n')
sys.stderr.write(str(titleablechars) + ' characters with a distinct title-case\n')
sys.stderr.write(str(totalspecialcases) + ' characters with length changes\n')
sys.stderr.write(str(len(specialtable)) + ' special-case characters\n')

for val in casetable.keys():
    (upcase, downcase, titlecase) = casetable[val]

    blocknum = val >> 8
    if (not blocktable.has_key(blocknum)):
        block = [ None ] * 256
        blocktable[blocknum] = block
    else:
        block = blocktable[blocknum]
    block[val & 0xFF] = (upcase, downcase)

print '/* This file was generated by casemap.py. */'
print

blockkeys = blocktable.keys()
blockkeys.sort()

for blocknum in blockkeys:
    print 'static gli_case_block_t unigen_case_block_' + hex(blocknum) + '[256] = {'
    block = blocktable[blocknum]
    for ix in range(256):
        ch = blocknum * 0x100 + ix
        res = block[ix]
        if (res == None):
            upcase = ch
            downcase = ch
        else:
            (upcase, downcase) = res
        if (specialtable.has_key(ch)):
            print '    { 0xFFFFFFFF, 0xFFFFFFFF },'
        else:
            if (upcase != downcase):
                if (upcase == ch):
                    comment = '  /* upper */'
                elif (downcase == ch):
                    comment = '  /* lower */'
                else:
                    comment = '  /* different */'
            else:
                comment = ''
            print '    { ' + hex(upcase) + ', ' + hex(downcase) + ' },' + comment
    print '};'
    print

print '#define GET_CASE_BLOCK(ch, blockptr)  \\'
print 'switch ((glui32)(ch) >> 8) {  \\'
for blocknum in blockkeys:
    print '    case ' + hex(blocknum) + ':  \\'
    print '        *blockptr = unigen_case_block_' + hex(blocknum) + ';  \\'
    print '        break;  \\'
print '    default:  \\'
print '        *blockptr = NULL;  \\'
print '}'

specialkeys = specialtable.keys()
specialkeys.sort()

pos = 0
specialstructs = []

print 'static glui32 unigen_special_array[] = {'

for val in specialkeys:
    speccase = specialtable[val]
    (upcasel, downcasel, titlecasel) = speccase
    
    comment = '  /* ' + hex(val) + ' upcase */'
    strarr = ', '.join([hex(st) for st in upcasel])
    print '    ' + str(len(upcasel)) + ', ' + strarr + ',' + comment
    pos0 = pos
    pos = pos + len(upcasel) + 1
    
    comment = '  /* ' + hex(val) + ' downcase */'
    strarr = ', '.join([hex(st) for st in downcasel])
    print '    ' + str(len(downcasel)) + ', ' + strarr + ',' + comment
    pos1 = pos
    pos = pos + len(downcasel) + 1

    comment = '  /* ' + hex(val) + ' titlecase */'
    strarr = ', '.join([hex(st) for st in titlecasel])
    print '    ' + str(len(titlecasel)) + ', ' + strarr + ',' + comment
    pos2 = pos
    pos = pos + len(titlecasel) + 1

    specialstructs.append( (val, pos0, pos1, pos2) )

print '};'
print

for (val, pos0, pos1, pos2) in specialstructs:
    print 'static gli_case_special_t unigen_special_' + hex(val) + ' = { ' + str(pos0) + ', ' + str(pos1) + ', ' + str(pos2) + ' };'

print

print '#define GET_CASE_SPECIAL(ch, specptr)  \\'
print 'switch (ch) {  \\'
for (val, pos0, pos1, pos2) in specialstructs:
    print '    case ' + hex(val) + ':  \\'
    print '        *specptr = unigen_special_' + hex(val) + ';  \\'
    print '        break;  \\'
print '    default:  \\'
print '        *specptr = NULL;  \\'
print '}'

print
