# -*- coding: utf-8 -*-
"""
Created on Thu Mar 15 14:51:11 2018

@author: Liaowei
"""
import pandas as pd
import numpy as np
import time
import datetime
import os

from utils import raw_data_path,feature_data_path,result_path,cache_pkl_path,dump_pickle,load_pickle,build_train_dataset,cal_log_loss,submmit_result
from smooth import BayesianSmoothing
import gen_smooth_features as smooth_features
from sklearn.linear_model import LogisticRegression
from sklearn.cross_validation import KFold,train_test_split
import lightgbm as lgb

params = {
    'max_depth': 4,                 #4
#    'min_data_in_leaf': 40,-
    'feature_fraction': 1,       #1
    'learning_rate': 0.04,          #0.04
    'boosting_type': 'gbdt',
    'objective': 'binary',
#    'verbose': -1,
    'metric': 'binary_logloss',
}

if __name__ == '__main__':
    
    
    t0 = time.time()
    train_data = load_pickle(path=cache_pkl_path +'train_data')
    train_Y = load_pickle(path=cache_pkl_path +'train_Y')
    
    cv_data = load_pickle(path=cache_pkl_path +'cv_data')
    cv_Y = load_pickle(path=cache_pkl_path +'cv_Y')
    
    test_data = load_pickle(path=cache_pkl_path +'test_data')
    
    rate = 0.75
    
    
    
    train_data = pd.concat([train_data, cv_data],axis=0)
    train_data = build_train_dataset(train_data, rate)
    train_Y = train_data['is_trade'].values
    drop_cols = ['is_trade']
    train_data.drop(drop_cols,axis=1,inplace=True)
    cv_data.drop(drop_cols,axis=1,inplace=True)
    test_data.drop(drop_cols,axis=1,inplace=True)
    
    print('train shap:',train_data.shape)
    print('cv shape', cv_data.shape)
    print('test shape', test_data.shape)
    
    kf = KFold(len(train_data), n_folds = 5, shuffle=True, random_state=520)
    train_preds = np.zeros(train_data.shape[0])
    cv_preds = np.zeros(train_data.shape[0])
    test_preds = np.zeros((test_data.shape[0], 5))
    for i, (train_index, cv_index) in enumerate(kf):
        print('第{}次训练...'.format(i))
        train_feat = train_data.iloc[train_index]
        cv_feat = train_data.iloc[cv_index]
    
        lgb_train = lgb.Dataset(train_feat.values, train_Y[train_index])
        lgb_cv = lgb.Dataset(cv_feat.values, train_Y[cv_index])
        gbm = lgb.train(params=params,
                        train_set=lgb_train,
                        num_boost_round=6000,
                        valid_sets=lgb_cv,
                        verbose_eval=False,
                        early_stopping_rounds=200)
        #评价特征的重要性
        feat_imp = pd.Series(gbm.feature_importance(), index=train_data.columns).sort_values(ascending=False)
        
        predict_train = gbm.predict(train_feat.values)
        predict_cv = gbm.predict(cv_feat.values)
        test_preds[:,i] = gbm.predict(test_data.values)
        
        train_preds[train_index] += predict_train
        cv_preds[cv_index] += predict_cv
        
        feat_imp = pd.Series(gbm.feature_importance(), index=train_data.columns).sort_values(ascending=False)
    
        print('   训练损失:',cal_log_loss(predict_train, train_Y[train_index]))
        print('   测试损失:',cal_log_loss(predict_cv, train_Y[cv_index]))
    predict_test = np.median(test_preds,axis=1)
    predict_test = predict_test/(predict_test+(1-predict_test)/rate)
    print('训练损失:',cal_log_loss(train_preds/4, train_Y))
    print('测试损失:',cal_log_loss(cv_preds, train_Y))
#    lgb_train = lgb.Dataset(train_data.values, train_Y)
#    lgb_cv = lgb.Dataset(cv_data.values, cv_Y)
#    gbm = lgb.train(params=params,            #参数
#                    train_set=lgb_train,      #要训练的数据
#                    num_boost_round=6000,     #迭代次数
#                    valid_sets=lgb_cv,        #训练时需要评估的列表
#                    verbose_eval=False,       #
#                    
#                    early_stopping_rounds=200)
#    
#    predict_train = gbm.predict(train_data.values)
#    predict_cv = gbm.predict(cv_data.values)
#    predict_test = gbm.predict(test_data.values)
#    
#    feat_imp = pd.Series(gbm.feature_importance(), index=train_data.columns).sort_values(ascending=False)
#
#    print('训练损失:',cal_log_loss(predict_train, train_Y))
#    print('测试损失:',cal_log_loss(predict_cv, cv_Y))
#    t1 = time.time()
#    print('训练时间:',t1 - t0)
#    
##    全量评测
#    train_data = pd.concat([train_data, cv_data],axis=0)
#    train_Y = np.append(train_Y, cv_Y)
#    
#    lgb_train = lgb.Dataset(train_data.values, train_Y)
#    gbm = lgb.train(params=params,            #参数
#                    train_set=lgb_train,      #要训练的数据
#                    num_boost_round=300,     #迭代次数
#                    verbose_eval=True)
#    predict_test = gbm.predict(test_data.values)
#    print('训练损失:',cal_log_loss(gbm.predict(train_data.values), train_Y))
    
    submmit_result(predict_test, 'LGB')
    
    
    