# -*- coding: utf-8 -*-
"""
Created on Tue Mar 15 10:15:42 2022

"""

#%% import libraries and put in path to csv's

#import libraries
import pandas as pd
import numpy as np

#put path to directory containing Inpatient claims and ICD-9 csv's here
#Note that '\' must be escaped using '\\', or you may use '/' depending on your OS. End with slash.
path_to_files = 'C:\\Users\\johna\\Desktop\\SchoolWork\\Data_Wrangling\\Data_Wrangling_Project\\'
#%% import csv data

DGNS_CD_len = 11 #number of DGNS columns + 1
PRCDR_CD_len = 7 #number of PRCDR columns + 1
#make list of relevant column names to extract from Inpatient Claims data
col_names = ['DESYNPUF_ID','CLM_ADMSN_DT','NCH_BENE_DSCHRG_DT']
col_names.extend(['ICD9_DGNS_CD_' + str(x) for x in range(1,DGNS_CD_len)])
col_names.extend(['ICD9_PRCDR_CD_' + str(x) for x in range(1,PRCDR_CD_len)])

#import Inpatient claims csv's
files_to_read = 1 #number of csv samples to read; must be 1-20
for i in range(1,files_to_read+1):
    if i == 1:
        inpatient_claims_df = pd.read_csv(path_to_files + 'DE1_0_2008_to_2010_Inpatient_Claims_Sample_'\
                                          + str(i) + '.csv', usecols=col_names)
    else:
        inpatient_add_df = pd.read_csv(path_to_files + 'DE1_0_2008_to_2010_Inpatient_Claims_Sample_'\
                                       + str(i) + '.csv', usecols=col_names)
        inpatient_claims_df = pd.concat([inpatient_claims_df,inpatient_add_df])

#import ICD-9 codes csv's

ICD9_DG_df = pd.read_excel(path_to_files + 'CMS28_DESC_LONG_SHORT_DX.xls',index_col=[0])
ICD9_SG_df = pd.read_excel(path_to_files + 'CMS28_DESC_LONG_SHORT_SG.xls',index_col=[0])

#%% Mark up ICD-9 files with relevant quality measures; clean up datatypes

#Add columns to ICD-9 df's to mark codes relevant to quality measures; initialize these columns with zeroes
zero_list_DG = [0 for x in range(ICD9_DG_df.shape[0])]
ICD9_DG_df['SSI'],ICD9_DG_df['DVT'] = [zero_list_DG,zero_list_DG]
zero_list_SG = [0 for x in range(ICD9_SG_df.shape[0])]
ICD9_SG_df['Surgical_Proc'] = zero_list_SG

#convert int dtypes to str
inpatient_claims_df['ICD9_PRCDR_CD_1'] = inpatient_claims_df['ICD9_PRCDR_CD_1'].astype(str)
ICD9_SG_df.index = ICD9_SG_df.index.astype(str)

#converts dates to datetime format
inpatient_claims_df['CLM_ADMSN_DT'] = pd.to_datetime(inpatient_claims_df['CLM_ADMSN_DT'],format="%Y%m%d")
inpatient_claims_df['NCH_BENE_DSCHRG_DT'] = pd.to_datetime(inpatient_claims_df['NCH_BENE_DSCHRG_DT'],format="%Y%m%d")
#%% Mark up Inpatient Claims df's with rows containing relevant measures

#Markup Surgery codes in inpatient claims df
inpatient_claims_df['Surgical_PRCDR'] = [0 for x in range(inpatient_claims_df.shape[0])]
for index,row in inpatient_claims_df.iterrows(): #couldn't think of a clean and flexible way to do this with .map(), etc.
    for x in range(1,PRCDR_CD_len):
        try: #if there's a nan or index is not found, continue to the next one
            if ICD9_SG_df.loc[row['ICD9_PRCDR_CD_' + str(x)]]['Surgical_Proc'] == 1:
                row['Surgical_PRCDR'] = 1 #add one or just set it as one?
        except:
            continue

#Markup diagnosis codes in inpatient claims df
inpatient_claims_df['SSI'],inpatient_claims_df['DVT'] = [0 for x in range(inpatient_claims_df.shape[0])],[0 for x in range(inpatient_claims_df.shape[0])]
for index,row in inpatient_claims_df.iterrows(): #couldn't think of a clean and flexible way to do this with .map(), etc.
    for x in range(1,DGNS_CD_len):
        try: #if there's a nan or index is not found, continue to the next one
            if ICD9_DG_df.loc[row['ICD9_DGNS_CD_' + str(x)]]['SSI'] == 1:
                row['SSI'] = 1 #add one or just set it as one?
            if ICD9_DG_df.loc[row['ICD9_DGNS_CD_' + str(x)]]['DVT'] == 1:
                row['DVT'] = 1 #add one or just set it as one?
        except:
            continue
#%% LOS calculation
LOS_list = (inpatient_claims_df['NCH_BENE_DSCHRG_DT'] - inpatient_claims_df['CLM_ADMSN_DT']).apply(lambda x: x.days).tolist()
#from here you could do a rolling average, make a histogram, gather estimators, etc.
#%%Readmission, SSI, DVT, reoperation counts -- This code needs to be tested
zero_list_inpatient = [0 for x in range(inpatient_claims_df.shape[0])]
inpatient_claims_df['counted_Proc'],inpatient_claims_df['counted_SSI'],inpatient_claims_df['counted_DVT'],inpatient_claims_df['counted_reop'] = zero_list_inpatient,zero_list_inpatient,zero_list_inpatient,zero_list_inpatient
readmission_tf = 30 #timeframe (in days) for how close to surgery is considered a readmission
SSI_tf = 30 #timeframe (in days) for how close to surgery is considered an SSI
DVT_tf = 30 #timeframe (in days) for how close to surgery is considered a DVT
reop_tf = 3 #timeframe (in days) for how close to surgery is considered a reoperation
readmission_count = 0
SSI_count = 0
DVT_count = 0
reop_count = 0
inpatient_claims_grouped = inpatient_claims_df.groupby('DESYNPUF_ID')
for name,group in inpatient_claims_grouped:
    for index,row in group.iterrows():
        if row['Surgical_PRCDR'] == 1:
            for index2,row2 in group.iterrows():
                time_diff = (row2['CLM_ADMSN_DT'] - row['CLM_ADMSN_DT']).days
                #not sure about readmission criteria. Does it need to be a surgery? If not,
                #get rid of first conditional.
                if row2['Surgical_PRCDR'] == 1\
                and row2['counted_Proc'] == 0\
                and time_diff > 0\
                and time_diff <= readmission_tf:
                    readmission_count += 1
                    row2['counted_Proc'] = 1
                if row2['SSI'] == 1\
                and row2['counted_SSI'] == 0\
                and time_diff > 0\
                and time_diff <= SSI_tf:
                    SSI_count += 1
                    row2['counted_SSI'] = 1
                if row2['DVT'] == 1\
                and row2['counted_DVT'] == 0\
                and time_diff > 0\
                and time_diff <= DVT_tf:
                    DVT_count += 1
                    row2['counted_DVT'] = 1
                #Put surgical reop conditionals here.
                #Does surgical reop need to be the same ICD9 code? If yes,
                #the whole list of PRCDR codes in 'row' must be compared to
                #the whole list of PRCDR codes in 'row2'




import seaborn as sns
import matplotlib.pyplot as plt 
#Visualizations-waiting on other metrics to work before deciding plots 
#Length of Stay 
sns.histplot(LOS_list, binwidth = 3)
plt.title("Length of Stay Distribution")
plt.xlabel("Days");


























