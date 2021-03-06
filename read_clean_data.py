# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import precision_recall_fscore_support as prfs
import matplotlib.pyplot as plt
from functools import reduce
import os
import re

datadir = "data/UCI_HAR_Dataset/"

# should be a way to do this all in one regex
def parseColumn(ss):
    pat1 = re.compile('[\(\)]')
    pat2 = re.compile('(.*)(\d+),(\d+)')
    pat3 = re.compile('(.*)([XYZ]),([XYZ1234])')
    pat4 = re.compile('[-]')
    pat5 = re.compile('(Body|Mag|,)')  # 469
#    pat5 = re.compile('(Body|,)')    # 477
    
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
    tt = re.sub(pat5, '', tt)  # removal changes dup count to 477
    tt = tt.replace('mean','Mean')
    tt = tt.replace('std','Std')
    tt = tt.replace('gravity','_gravity')
    tt = tt.replace('angle','angle_')
    return tt

# test parseColumn()
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

def readRawColumns(printOut=False):
    '''read raw data columns'''
    feature_file = datadir + "features.txt"
    dfcol = pd.read_csv(feature_file, sep='\s+', header=None, index_col=0)
    dfcol.columns=['label']
    
    dfcol['label'] = dfcol['label'].apply(lambda s: parseColumn(s))
    
    # make unique column names, assign to label2
    hh = {}
    dlist = []
    for c in dfcol['label']:
        if c in hh.keys():
            hh[c] += 1
            dlist.append(c + '_' + str(hh[c]))
        else:
            hh[c] = 0
            dlist.append(c)
    dfcol['label2'] = dlist

    if (printOut==True):
        print('dfcol\n', dfcol[:5])    
        print('dfcol shape', dfcol.shape)

    # check duplicate columns    
    dups = [k for (k,v) in hh.items() if v > 1]
    dups = sorted(dups)
    
    return dfcol, dups

def readActivityLabels():
    '''read activity labels'''
    dfact = pd.read_table(datadir + "activity_labels.txt", \
        sep='\s+', header=None, index_col=0)
    dfact.columns=['act']
    return dfact

def readRawTrainData(dfcol, dfact, printOut=False):
    '''read in raw train data'''
    traindir = datadir + "train/"
    dftrain = pd.read_table(traindir + "X_train.txt", \
        sep='\s+', header=None, names=dfcol['label2'])
    dftrain['subject'] = pd.read_table(traindir + "subject_train.txt", \
        sep='\s+', header=None)
    dftrain_y = pd.read_table(traindir + "y_train.txt", \
        sep='\s+', header=None, names=['Y'])
    dftrain_y['activity'] = dftrain_y['Y'].apply(lambda x: \
        dfact['act'][dfact.index[x-1]])
    if (printOut==True):
        print("dftrain head\n", dftrain[:5])
        print("dftrain_y shape", dftrain_y.shape, "head\n", dftrain_y[295:305])
    return dftrain, dftrain_y

def readRawTestData(dfcol, dfact, printOut=False):
    testdir = datadir + "test/"
    dftest = pd.read_table(testdir + "X_test.txt", \
        sep='\s+', header=None, names=dfcol['label2'])
    dftest['subject'] = pd.read_table(testdir + "subject_test.txt", \
        sep='\s+', header=None)
    dftest_y = pd.read_table(testdir + "y_test.txt", \
        sep='\s+', header=None, names=['Y'])
    dftest_y['activity'] = dftest_y['Y'].apply(lambda x: \
        dfact['act'][dfact.index[x-1]])
    if (printOut==True):
        print("dftest head", dftest.shape, "\n", dftest[:5])
        print("dftest_y shape", dftest_y.shape, "head\n", dftest_y[:5])
    return dftest, dftest_y

def readRawData(dfcol, printOut=False):
    dfact = readActivityLabels()
    dftrain, dftrain_y = readRawTrainData(dfcol, dfact, printOut)
    dftest, dftest_y = readRawTestData(dfcol, dfact, printOut)
    return dftrain, dftrain_y, dftest, dftest_y

def checkDuplicateColumns(dfcol, dups, dftrain):
    '''check duplicate columns'''
    print("DUPS, len =", len(dups))
    for dup in dups:
        dg = list(filter(lambda s: s.startswith(dup), \
            dfcol['label2']))
        dt = dftrain[dg]
        print("dt dup %s mean" % dup)
        print(dt.mean())
# values, mean are close but not identical, within 3-4 places

def removeDuplicateColumns(dfcol, dups, dftrain, dftest):
    '''find duplicate columns to remove from dataframe'''
    dg = list(map(lambda dup: list(filter(lambda s: \
        s.startswith(dup+"_"), dfcol['label2'])), dups))
    dg = [item for sublist in dg for item in sublist]
    dftrain = dftrain.drop(dg, axis=1)
    dftest = dftest.drop(dg, axis=1)
    return dftrain, dftest

def rfFitScore(clf, dftrain, dftrain_y, dftest, dftest_y):
    '''random forest classifier fit and score.
       clf=RandomForestClassifier, dftrain=train data,
       dftrain_y=train data Y, dftest=test data,
       dftest_y=test data Y'''
    
    clfit = clf.fit(dftrain, dftrain_y['Y'])  # clf.fit(X, y)
    
    imp = clfit.feature_importances_  # ndarray of 562    
    # clfit.fit_transform( X, y=None )  # returns X_new
    
    new_y = clfit.predict( dftest )  # returns predicted Y
    
    test_score = clfit.score( dftest, dftest_y['Y'] )
    print("test score:", test_score)  # clfit.oob_score_  
    if (clf.oob_score):
        print("oob score", clfit.oob_score_)
    
    # calculate test score by other means
    print("predict True %.3f percent, %d out of %d" % \
      ((100 * sum(dftest_y['Y'] == new_y) / dftest_y.shape[0]), \
       sum(dftest_y['Y'] == new_y), dftest_y.shape[0]))
    print("predict False %.3f percent, %d out of %d" % \
      ((100 * sum(dftest_y['Y'] != new_y) / dftest_y.shape[0]), \
       sum(dftest_y['Y'] != new_y), dftest_y.shape[0]))
    
#    new_p = clfit.predict_proba( dftest )
#    # probability of each X variable to predict each y class
#    print("test predict probabilities head:\n", new_p[:5])
    
    # cross table of variable predictions
    ptab = pd.crosstab(dftest_y['Y'], new_y, \
        rownames=['actual'], colnames=['predicted'])
    print("cross table:\n", ptab)
    
    # accuracy: percent labeled correctly
    # precision: true positives / (true positives + true negatives)
    # recall:    true positives / (true positives + false negatives)
    precision, recall, fbeta, support = prfs(dftest_y['Y'], new_y)
    print("precision", precision, "\nrecall", recall, \
        "\nfbeta", fbeta, "\nsupport", support)
    
    if (clf.oob_score):
        return test_score, imp, clfit.oob_score_
    else:
        return test_score, imp

def getImportantColumns(dftraincol, imp):
    '''sort column names by RandomForest importance
       for use in dftrain, dftest subset'''
    return sorted(zip(imp, dftraincol), reverse=True)

def getPlotDir():
    plotdir = "human_activity_plots/"
    if not os.access(plotdir, os.F_OK):
        os.mkdir(plotdir)
    return plotdir

def plotImportances(impcol, plotdir, label):
    vals = list(map(lambda e: e[0], impcol))
    valsum = np.cumsum(vals)
    vals = vals / vals[0]     # norm
    
    plt.clf()
    plt.plot(range(len(vals)), vals)
    plt.plot(range(len(valsum)), valsum)
    plt.ylim(0.0, 1.0)
    plt.xlabel("Feature Number")
    plt.ylabel("Importance")
    plt.title("Human Activity: Random Forest Importances")
    plt.legend(('relative importance', 'cumulative importance'), \
        loc='center right')
    plt.savefig(plotdir + "impt_" + label)    
    
    plt.clf()
    plt.plot(range(100), vals[:100])
    plt.plot(range(100), valsum[:100])
    plt.ylim(0.0, 1.0)
    plt.xlabel("Feature Number")
    plt.ylabel("Importance")
    plt.title("Human Activity: Random Forest Importances")
    plt.legend(('relative importance', 'cumulative importance'), \
        loc='upper center')
    plt.text(70, 0.35, "First Hundred\nImportances")
    plt.savefig(plotdir + "impt100_" + label)

def plotHistograms(dftrain, dftrain_y, plotdir):
    # pick a few labels likely to distinguish classes
    labels = ['tAcc_Mean', 'fAcc_Mean', 'tGyro_Mean', 'fBGyro_Mean']
    for label in labels:
        plt.clf()
        dftrain[label].hist(by=dftrain_y['activity'], \
            sharex=True, xlabelsize=8, ylabelsize=8)
        plt.text(-2.5, -170, "Histograms of " + label + " by Activity")
        plt.savefig(plotdir + "hist_" + label)

# only works if one parameter explored
def gridscoreBoxplot(gslist, plotdir, label, xlabel):
    vals = list(map(lambda e: e.cv_validation_scores, gslist))
    labs = list(map(lambda e: list(e.parameters.values()), gslist))
    labs = list(map(lambda e: str(e[0]), labs))
    plt.clf()
    plt.boxplot(vals, labels=labs)
    plt.title("Human Activity Fitted by Random Forest")
    plt.xlabel(label + " (with " + xlabel + ")")
    plt.ylabel("Fraction Correct")
    plt.savefig(plotdir + "gridscore_" + label)

def main():
    dfcol, dups = readRawColumns(printOut=True)
    dftrain, dftrain_y, dftest, dftest_y = readRawData(dfcol, printOut=True)
    
    plotdir = getPlotDir()
    plotHistograms(dftrain, dftrain_y, plotdir)
    
    # first analysis: remove columns w/ duplicate names
    print("\nRemove columns with duplicate names")
    dftrain, dftest = removeDuplicateColumns(dfcol, dups, dftrain, dftest)
    print("dftrain head", dftrain.shape, "\n", dftrain[:5])    
    
    # check that random forest works
    print("Basic check")
    clf = RandomForestClassifier(n_estimators=10)
    score, imp = rfFitScore(clf, dftrain, dftrain_y, dftest, dftest_y)
    impcol = getImportantColumns(dftrain.columns, imp)
    print("Basic check: Top ten important columns:\n", impcol[:10])

# Cross table shows ~10 percent covariance within
#   sedentary activities (LAYING SITTING STANDING)
#   and within active activities (WALKING UPSTAIRS DOWNSTAIRS),
#   but almost no covariance between active and 
#   sedentary activities.

#   should give overfitting
    print("Overfit")
    clf = RandomForestClassifier(n_estimators=20)
    score, imp = rfFitScore(clf, dftrain, dftrain_y, dftrain, dftrain_y)
    impcol = getImportantColumns(dftrain.columns, imp)
    print("Overfit: Top ten important columns:\n", impcol[:10])
    
#    split training, test sets into train, validate, test
#    use dftrain, dfvalid to find top ten columns

# add subject to Y's for validation split
    cutoff = 23
    dftrain_y['subject'] = dftrain['subject']
    dfvalid = dftrain[dftrain['subject'] > cutoff]
    dftrain = dftrain[dftrain['subject'] <= cutoff]
    dfvalid_y = dftrain_y[dftrain_y['subject'] > cutoff]
    dftrain_y = dftrain_y[dftrain_y['subject'] <= cutoff]
    dftrain_y = dftrain_y.drop(['subject'], axis=1)
    dfvalid_y = dfvalid_y.drop(['subject'], axis=1)
    
    # find optimum n_estimators if possible
    clf = RandomForestClassifier(max_features='sqrt')
    param_grid = [{'n_estimators': [ 50, 100, 200, 500 ] }]
    gs = GridSearchCV(estimator=clf, param_grid=param_grid, cv=3, \
      verbose=1, n_jobs=-1)    # verbose=10
    gs.fit(dftrain, dftrain_y['Y'])
    print("gs grid scores\n", gs.grid_scores_)
    print("gs best score %.5f %s\n%s" % \
      (gs.best_score_, gs.best_params_, gs.best_estimator_))
    gridscoreBoxplot(gs.grid_scores_, plotdir, "n_estimators", "max_features=sqrt")
    new_y = gs.predict(dfvalid)  # predict on gs.best_params_
    print("gs score %.5f (%d of %d)" % (gs.score(dfvalid, dfvalid_y['Y']), \
      sum(new_y == dfvalid_y['Y']), dfvalid_y.shape[0] ))
    
    # find optimum max_features if possible  # sqrt(478)~22 log2(478)~9
    clf = RandomForestClassifier(n_estimators=100)
    param_grid = [{'max_features': [None, 'auto', 'sqrt', 'log2', \
        9, 15, 22, 44, 100 ] }]
    gs = GridSearchCV(estimator=clf, param_grid=param_grid, cv=3, \
      verbose=1, n_jobs=-1)    # verbose=10
    gs.fit(dftrain, dftrain_y['Y'])
    print("gs grid scores\n", gs.grid_scores_)
    print("gs best score %.5f %s\n%s" % \
      (gs.best_score_, gs.best_params_, gs.best_estimator_))
    gridscoreBoxplot(gs.grid_scores_, plotdir, "max_features", "n_estimators=100")
    new_y = gs.predict(dfvalid)  # predict on gs.best_params_
    print("gs score %.5f (%d of %d)" % (gs.score(dfvalid, dfvalid_y['Y']), \
      sum(new_y == dfvalid_y['Y']), dfvalid_y.shape[0] ))
    
    # plot importances, curve better defined for higher n_est
    print("Validation n=100")
    clf = RandomForestClassifier(n_estimators=100, max_features='auto')
    score, imp = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
    impcol = getImportantColumns(dftrain.columns, imp)
    print("n=100 fit: top ten important columns:\n", impcol[:10])
    plotImportances(impcol, plotdir, "vb100")  # score 0.9073
    
    print("Validation n=200")
    clf = RandomForestClassifier(n_estimators=200, max_features='auto')
    score, imp = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
    impcol = getImportantColumns(dftrain.columns, imp)
    print("n=200 fit: top ten important columns:\n", impcol[:10])
    plotImportances(impcol, plotdir, "vb200")  # score 0.9068
    
    print("Validation n=500")
    clf = RandomForestClassifier(n_estimators=500, max_features='auto')
    score, imp = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
    impcol = getImportantColumns(dftrain.columns, imp)
    print("n=500 fit: top ten important columns:\n", impcol[:10])
    plotImportances(impcol, plotdir, "vb500")  # score 0.9064
    
    # get avg score and oob_score
    scores = []
    oobs = []
    for i in list(range(3)):  # average of three
        print("Validation n=100")
        clf = RandomForestClassifier(n_estimators=100, max_features='auto', oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("n=100 fit: top ten important columns:\n", impcol[:10])
        scores.append(score)
        oobs.append(oob)
        
        print("Validation n=200")
        clf = RandomForestClassifier(n_estimators=200, max_features='auto', oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("n=200 fit: top ten important columns:\n", impcol[:10])
        
        print("Validation n=500")
        clf = RandomForestClassifier(n_estimators=500, max_features='auto', oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("n=500 fit: top ten important columns:\n", impcol[:10])
    
    print("valid scores mean %.5f, std %.5f" % (np.mean(scores), np.std(scores)))
    print("valid oobs mean %.5f, std %.5f" % (np.mean(oobs), np.std(oobs)))
    
    new_y = clf.predict(dftest)  # uses last clf.fit()
    print("clf score %.4f (%d of %d)" % (clf.score(dftest, dftest_y['Y']), \
      sum(new_y == dftest_y['Y']), dftest_y.shape[0] ))

    scores = []
    oobs = []
    # predict optimum params with dftest
    print("Test model fit")
    for i in list(range(3)):  # average of three
        clf = RandomForestClassifier(n_estimators=100, max_features='auto', oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dftest, dftest_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("Test model fit: top ten important columns:\n", impcol[:10])
        scores.append(score)
        oobs.append(oob)
    print("test auto scores mean %.5f, std %.5f" % (np.mean(scores), np.std(scores)))
    print("test auto oobs mean %.5f, std %.5f" % (np.mean(oobs), np.std(oobs)))

    scores = []
    oobs = []
    # predict optimum params with dftest
    print("Test model fit")
    for i in list(range(3)):  # average of three
        clf = RandomForestClassifier(n_estimators=100, max_features='log2', oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dftest, dftest_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("Test model fit: top ten important columns:\n", impcol[:10])
        scores.append(score)
        oobs.append(oob)
    print("test log2 scores mean %.5f, std %.5f" % (np.mean(scores), np.std(scores)))
    print("test log2 oobs mean %.5f, std %.5f" % (np.mean(oobs), np.std(oobs)))

    print("activity labels:\n", readActivityLabels())

if __name__ == '__main__':
    main()

