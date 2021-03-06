# -*- coding: utf-8 -*-

# predict human activity after reading and cleaning data
# use Random Forest w/ all anonymous variable names

#import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from functools import reduce
from sklearn.ensemble import RandomForestClassifier
from sklearn import cross_validation
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix

from read_clean_data import readRawColumns, readRawData, rfFitScore, \
    getImportantColumns, getPlotDir

def renameColumns(df):
    '''rename columns x0-xn except subject and activity (latter is Y)'''
    dlen = df.shape[1] - 1  # assume last column stays same
    newcol = list(map(lambda s: "x" + str(s), list(range(dlen))))
    newcol.append(df.columns[-1])
    df.columns = newcol
    return df

# six subjects total, not all subjects in dftrain
def getValidationData(dfx):
    '''get validation data'''
    return dfx[(dfx['subject'] >= 19) & (dfx['subject'] < 27)]

def plotConfusionMatrix(cm, plotdir, label, target_names):
    print("confusion matrix") 
    print(cm)
    plt.clf()
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    title='Random Forest: Confusion matrix ' + label
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(target_names))
    plt.xticks(tick_marks, target_names)  # rotation=45
    plt.yticks(tick_marks, target_names)
    plt.tight_layout()  # adds padding
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.savefig(plotdir + label + '_conf_mat')

# only works if more than one element per labs entry
def gridscoreBoxplot2(gslist, plotdir, label, xlabel):
    vals = list(map(lambda e: e.cv_validation_scores, gslist))
    labs = list(map(lambda e: list(e.parameters.values()), gslist))
# test if labs[0].__class__ == 'list' and len(labs[0]) > 1
    labs = list(map(lambda e: reduce(lambda a,b: str(a)+"\n"+str(b), e), labs))
    xpar = list(gslist[0].parameters.keys())
    xpar = reduce(lambda a,b: a+", "+b, xpar)
    plt.clf()
    plt.boxplot(vals, labels=labs)
    plt.title("Human Activity Fitted by Random Forest")
    plt.xlabel(xpar + " (with " + xlabel + ")")
    plt.ylabel("Fraction Correct")
    plt.tight_layout()
    plt.savefig(plotdir + "gridscore_" + label)

if __name__ == '__main__':
    dfcol, dups = readRawColumns()
    dftrain, dftrain_y, dftest, dftest_y = readRawData(dfcol)
    
    dftrain = renameColumns(dftrain)
    dftest = renameColumns(dftest)
    print("dftrain shape head", dftrain.shape, "\n", dftrain[:5])
    print("dftest shape head", dftest.shape, "\n", dftest[:5])
    
    plotdir = getPlotDir()
    
    # which subjects?
    subjtrain = set(list(dftrain['subject']))
    subjtest = set(list(dftest['subject']))
    print("train subject set ( size", len(subjtrain), ")", subjtrain)
    print("test subject set ( size", len(subjtest), ")", subjtest)
# raw train, test data is in separate files, different subjects
# let's do quick and easy way: train>=27, test<=6, validate>=21 <27

    # add subject to y's before split
    dftrain_y['subject'] = dftrain['subject']
    dftest_y['subject'] = dftest['subject']
    
    dfvalid = getValidationData(dftrain)     # six subjects total
    dfvalid_y = getValidationData(dftrain_y)
    dfvalid_y = dfvalid_y.drop('subject', axis=1)
    print("dfvalid shape head", dfvalid.shape)
    print("dfvalid_y shape head", dfvalid_y.shape)
    
    dftest = dftest[dftest['subject'] < 14]  # six subjects total
    dftest_y = dftest_y[dftest_y['subject'] < 14]
    dftest_y = dftest_y.drop('subject', axis=1)
    print("dftest shape head", dftest.shape)
    print("dftest_y shape head", dftest_y.shape)
    
    dftrain = dftrain[dftrain['subject'] >= 27]  # four subjects total
    dftrain_y = dftrain_y[dftrain_y['subject'] >= 27]
    dftrain_y = dftrain_y.drop('subject', axis=1)
    print("dftrain shape head", dftrain.shape, "\n", dftrain[:2])
    print("dftrain_y shape head", dftrain_y.shape, "\n", dftrain_y[:2])
    
    # really what I want with validation is try several parameters
    scores = []
    oobs = []
    for i in list(range(5)):  # average of five
        print("Validation n=100")
        clf = RandomForestClassifier(n_estimators=100, oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("n=100 fit: top ten important columns:\n", impcol[:10])
        scores.append(score)
        oobs.append(oob)

    print("Valid scores mean, std", np.mean(scores), np.std(scores))
    print("Valid oobs mean, std", np.mean(oobs), np.std(oobs))
    # about 0.83
    
    clf = RandomForestClassifier(n_estimators=100, oob_score=True)
    # don't need to split train, valid
    scores = cross_validation.cross_val_score(clf, \
        dftrain, dftrain_y['Y'], cv=4)
    print("\nCV scores:", scores)
    print("CV scores mean, std", np.mean(scores), np.std(scores))
    
    # find optimum parameters if possible
    clf = RandomForestClassifier(oob_score=True)  # n_estimators=50
    param_grid = [{'n_estimators': [100, 200, 500], \
      'max_features': ['sqrt', 'log2'] }]
    gs = GridSearchCV(estimator=clf, param_grid=param_grid, cv=5, \
      verbose=1, n_jobs=-1, scoring='accuracy')    # verbose=10
    # scoring='accuracy', 'f1_weighted', 'precision_weighted'
    
    gs.fit(dftrain, dftrain_y['Y'])  # fits all training parameters
    print("gs grid scores\n", gs.grid_scores_)
    print("gs best score %.4f %s\n%s" % \
      (gs.best_score_, gs.best_params_, gs.best_estimator_))
    # all mean within 2 * std of each other, best not meaningful 
    gridscoreBoxplot2(gs.grid_scores_, plotdir, "multi_opt", "oob_score=True")
    
#   clf = gs.best_estimator_
#     n_estimators = 100 sufficient, more about the same
#     max_features=log2 not much different than auto
#   set optimum by hand
    
    print("validating optimum params")
    scores = []
    oobs = []
    for i in list(range(5)):  # average of five
        print("Test optimum")
        clf = RandomForestClassifier(n_estimators=100, max_features='sqrt', oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dfvalid, dfvalid_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("valid opt fit: top ten important columns:\n", impcol[:10])
        scores.append(score)
        oobs.append(oob)
    print("Valid scores mean, std", np.mean(scores), np.std(scores))
    print("Valid oobs mean, std", np.mean(oobs), np.std(oobs))    
    
    print("testing optimum params")
    scores = []
    oobs = []
    for i in list(range(5)):  # average of five
        print("Test optimum")
        clf = RandomForestClassifier(n_estimators=100, max_features='sqrt', oob_score=True)
        score, imp, oob = rfFitScore(clf, dftrain, dftrain_y, dftest, dftest_y)
        impcol = getImportantColumns(dftrain.columns, imp)
        print("opt fit: top ten important columns:\n", impcol[:10])
        scores.append(score)
        oobs.append(oob)
    print("Test scores mean, std", np.mean(scores), np.std(scores))
    print("Test oobs mean, std", np.mean(oobs), np.std(oobs))

#   get classification report, confusion matrix on last fit
    new_y = clf.predict(dftest)
    print("clf score %.4f (%d of %d)" % (clf.score(dftest, dftest_y['Y']), \
      sum(new_y == dftest_y['Y']), dftest_y.shape[0] ))
    print("\nclassification_report\n", classification_report(dftest_y['Y'], new_y))
    cm = confusion_matrix(dftest_y['Y'], new_y)
    plotConfusionMatrix(cm, plotdir, 'opt', list(sorted(set(dftest_y['Y']))))

#   find original labels of importances
#   for last test fit, just get a sense of it
    impcol2 = getImportantColumns(dfcol['label2'], imp)
    print("Top ten importances of last opt fit, by original name:\n", \
        list(map(lambda e: e[1], impcol2))[:10] )

