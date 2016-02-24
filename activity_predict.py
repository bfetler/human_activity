# -*- coding: utf-8 -*-

import pandas as pd
from functools import reduce
import os
import re

# init data

datadir = "data/UCI_HAR_Dataset/"

feature_file = datadir + "features.txt"
dfcol = pd.read_csv(feature_file, sep='\s+', header=None, index_col=0)
dfcol.columns=['label']
print('dfcol\n', dfcol)

# should be a way to do this all in one regex
def parseColumn(ss):
    pat1 = re.compile('[\(\)]')
    pat2 = re.compile('(.*)(\d+),(\d+)')
    pat3 = re.compile('(.*)([XYZ]),([XYZ1234])')
    pat4 = re.compile('[-]')
#    pat5 = re.compile('(Body|Mag|,)')  # 469
    pat5 = re.compile('(Body|,)')    # 477
    
    def splitJoin(pat, s):
        t = re.split(pat, s)
        return reduce(lambda a,b: a+b, t)
    
    def splitJoinNum(s):
        '''join two numbers with underscore'''
        t = re.split(pat2, s)
        if len(t) > 4:
            u = t[0] + t[1] + t[2] + '_' + t[3]
        else:
            u = reduce(lambda a,b: a+b, t)
        return u
    
    tt = re.sub(pat1, '', ss)
    tt = splitJoinNum(tt)
    tt = splitJoin(pat3, tt)
    tt = re.sub(pat4, '_', tt)
    tt = tt.replace('BodyBody', 'BBody')
    tt = re.sub(pat5, '', tt)  # removal chnages dup count to 477
    tt = tt.replace('mean','Mean')
    tt = tt.replace('std','Std')
    tt = tt.replace('gravity','_gravity')
    tt = tt.replace('angle','angle_')
    return tt

# ss = 'tBodyGyroJerk(Mag)-arCoeff()4)'
# ss = 'fBodyAcc-mad()-Y'
# ss = 'tBodyAccJerk-correlation()-Y,Z'
# ss = 'tBodyGyroJerk-arCoeff()-X,3'
# ss = 'fBodyBodyGyroMag-max()'
# ss = 'fBodyAcc-bandsEnergy()-9,16'
# ss = 'angle(tBodyAccJerkMean),gravityMean)'
# ss = 'fBodyAcc-max()-Z'
# ss = 'fBodyAcc-mean()-X'
# ss = 'tGravityAccMag-std()'

# tt = parseColumn(ss)
# print('tt', tt)

dfcol['label'] = dfcol['label'].apply(lambda s: parseColumn(s))
dfcol['label2'] = dfcol.index
dfcol['label2'] = dfcol['label'] + \
    dfcol['label2'].apply(lambda i: '_' + str(i))
print('dfcol\n', dfcol)
print("dfcol2", dfcol['label2'][:5])

print('yaa',dfcol.shape[0])
# // 2 since sypder buffer size is small
# for i in range(dfcol.shape[0]//2):
#     print(dfcol['label'][i+1+dfcol.shape[0]//2])
clist = list(dfcol['label'])

print('head clist', len(clist), clist[:5])  # 561
cset = set(clist)
print('head cset', len(cset), list(cset)[:5])  # 469
print('done')

# read in whole dataframe before removing duplicate columns?
# count duplicates, rename w/ counter, check if columns equal?
# 561 - 469 = 92 duplicates

# cc = []
# for c in clist:
#     cc.append( clist.count(c) )
# cc = list(map(clist.count. clist))
# print('cc', cc[:5])

# activity labels
dfact = pd.read_table(datadir + "activity_labels.txt", \
    sep='\s+', header=None, index_col=0)
dfact.columns=['act']
print("dfact\n", dfact)

# read in raw data
traindir = datadir + "train/"
dftrain = pd.read_table(traindir + "X_train.txt", \
    sep='\s+', header=None, names=dfcol['label2'])
dftrain['subject'] = pd.read_table(traindir + "subject_train.txt", \
    sep='\s+', header=None)
dftrain['Y'] = pd.read_table(traindir + "y_train.txt", \
    sep='\s+', header=None)
dftrain['YA'] = dftrain['Y'].apply(lambda x: dfact['act'][dfact.index[x-1]])
print("dftrain head\n", dftrain[:5])

testdir = datadir + "test/"
dftest = pd.read_table(testdir + "X_test.txt", \
    sep='\s+', header=None, names=dfcol['label2'])
dftest['subject'] = pd.read_table(testdir + "subject_test.txt", \
    sep='\s+', header=None)
dftest['Y'] = pd.read_table(testdir + "y_test.txt", \
    sep='\s+', header=None)
dftest['YA'] = dftest['Y'].apply(lambda x: dfact['act'][dfact.index[x-1]])
print("dftest head\n", dftest[:5])

# compare columns, check if duplicate names have duplicate values

# print('clist', len(clist), clist)


