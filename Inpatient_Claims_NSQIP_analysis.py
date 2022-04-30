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
col_names = ['DESYNPUF_ID','CLM_ADMSN_DT','NCH_BENE_DSCHRG_DT','PRVDR_NUM']
col_names.extend(['ICD9_DGNS_CD_' + str(x) for x in range(1,DGNS_CD_len)])
col_names.extend(['ICD9_PRCDR_CD_' + str(x) for x in range(1,PRCDR_CD_len)])

#import Inpatient claims csv's
files_to_read = 20 #number of csv samples to read; must be 1-20
for i in range(1,files_to_read+1):
    if i == 1:
        inpatient_claims_df = pd.read_csv(path_to_files + 'DE1_0_2008_to_2010_Inpatient_Claims_Sample_'\
                                          + str(i) + '.csv',dtype=str, usecols=col_names)
    else:
        inpatient_add_df = pd.read_csv(path_to_files + 'DE1_0_2008_to_2010_Inpatient_Claims_Sample_'\
                                       + str(i) + '.csv',dtype=str, usecols=col_names)
        inpatient_add_df.index += inpatient_claims_df.shape[0]
        inpatient_claims_df = pd.concat([inpatient_claims_df,inpatient_add_df])

#import ICD-9 codes csv's
#Note that read_csv tries to convert ICD9 codes to int (eg. codes 0050 and 050 both become a numeric 50 after conversion)
#dtype=str prevents this. Be careful to keep the codes as strings; set the codes as the index after import
ICD9_DG_df = pd.read_excel(path_to_files + 'CMS28_DESC_LONG_SHORT_DX.xls',dtype=str)
ICD9_SG_df = pd.read_excel(path_to_files + 'CMS28_DESC_LONG_SHORT_SG.xls',dtype=str)
ICD9_Surgery_df = pd.read_csv(path_to_files + 'surgery_flags_i9_2015.csv',skiprows=1,dtype=str,index_col=[0])
#Set ICD9 Surgery, ICD Procedure (SG), and ICD9 Diganosis (DG) codes as the indexes in the same string format
ICD9_Surgery_df.index = ICD9_Surgery_df.index.str.replace('\'','')
ICD9_SG_df.index = ICD9_SG_df['PROCEDURE CODE']
ICD9_SG_df = ICD9_SG_df.loc[:,['LONG DESCRIPTION','SHORT DESCRIPTION']]
ICD9_DG_df.index = ICD9_DG_df['DIAGNOSIS CODE']
ICD9_DG_df = ICD9_DG_df.loc[:,['LONG DESCRIPTION','SHORT DESCRIPTION']]

#import reop file
reop_code_df = pd.read_csv(path_to_files + "surgery_flags_i9_2015-MDA_Categorized_040622.csv")
reop_code_df.index = reop_code_df['\'ICD-9-CM CODE\''].str.replace('\'','')
reop_code_df = reop_code_df.loc[:,['Reop/Revision']]

#%% Mark up ICD-9 files with relevant quality measures; clean up datatypes

#converts dates to datetime format
inpatient_claims_df['CLM_ADMSN_DT'] = pd.to_datetime(inpatient_claims_df['CLM_ADMSN_DT'],format="%Y%m%d")
inpatient_claims_df['NCH_BENE_DSCHRG_DT'] = pd.to_datetime(inpatient_claims_df['NCH_BENE_DSCHRG_DT'],format="%Y%m%d")

#Add columns to ICD-9 df's to mark codes relevant to quality measures; initialize these columns with zeroes
zero_list_DG = [0 for x in range(ICD9_DG_df.shape[0])]
ICD9_DG_df['SSI'],ICD9_DG_df['DVT'] = zero_list_DG,zero_list_DG
zero_list_SG = [0 for x in range(ICD9_SG_df.shape[0])]
ICD9_SG_df['Surgical_Proc'],ICD9_SG_df['Reop'] = zero_list_SG,zero_list_SG

Surgery_df_index = ICD9_Surgery_df.index.tolist()
reop_index = reop_code_df[reop_code_df['Reop/Revision'] == 1].index.tolist()
for index,row in ICD9_SG_df.iterrows():
    if index in Surgery_df_index: #note that there are 225 codes in the surgery file that don't exist in the SG codes file
        ICD9_SG_df.at[index,'Surgical_Proc'] = 1
    if index in reop_index:
        ICD9_SG_df.at[index,'Reop'] = 1

SSI_codes = ['99859'] #ICD-9 codes for SSI
DVT_codes = ['9972'] #ICD-9 codes for DVT
for code in SSI_codes:
    ICD9_DG_df.loc[code,'SSI'] = 1
for code in DVT_codes:
    ICD9_DG_df.loc[code,'DVT'] = 1

#%% Optional method to quicken calculations; Reduces dfs to only rows containing 1's

ICD9_SG_df = ICD9_SG_df[(ICD9_SG_df == 1).any(axis=1)]
ICD9_DG_df = ICD9_DG_df[(ICD9_DG_df == 1).any(axis=1)]

#%% Mark up Inpatient Claims df's with rows containing relevant measures
#This may take a while to run

#Markup Surgery codes in inpatient claims df
timer = 0
codes_not_in_ICD9 = set()
inpatient_claims_df['Surgical_PRCDR'],inpatient_claims_df['Reop'] = [0 for x in range(inpatient_claims_df.shape[0])],[0 for x in range(inpatient_claims_df.shape[0])]
inpatient_claims_df['SSI'],inpatient_claims_df['DVT'] = [0 for x in range(inpatient_claims_df.shape[0])],[0 for x in range(inpatient_claims_df.shape[0])]
for index,row in inpatient_claims_df.iterrows(): #couldn't think of a clean and flexible way to do this with .map(), etc.
    for x in range(1,PRCDR_CD_len):
        if not pd.isna(row['ICD9_PRCDR_CD_' + str(x)]): #if there's a nan, continue to the next one
            if row['ICD9_PRCDR_CD_' + str(x)] in ICD9_SG_df.index:
                if ICD9_SG_df.loc[row['ICD9_PRCDR_CD_' + str(x)]]['Surgical_Proc'] == 1:
                    inpatient_claims_df.loc[index,'Surgical_PRCDR'] = 1
                if ICD9_SG_df.loc[row['ICD9_PRCDR_CD_' + str(x)]]['Reop'] == 1:
                    inpatient_claims_df.loc[index,'Reop'] = 1
            if row['ICD9_PRCDR_CD_' + str(x)] in ICD9_DG_df.index:
                if ICD9_DG_df.loc[row['ICD9_PRCDR_CD_' + str(x)]]['SSI'] == 1:
                    inpatient_claims_df.loc[index,'SSI'] = 1
                if ICD9_DG_df.loc[row['ICD9_PRCDR_CD_' + str(x)]]['DVT'] == 1:
                    inpatient_claims_df.loc[index,'DVT'] = 1
            #elif (row['ICD9_PRCDR_CD_' + str(x)] not in ICD9_SG_df.index):
                #codes_not_in_ICD9.add(row['ICD9_PRCDR_CD_' + str(x)])
    timer += 1
    if timer%50000 == 0:
        print(str(timer) + " rows completed for SG.")

timer=0
for index,row in inpatient_claims_df.iterrows(): #couldn't think of a clean and flexible way to do this with .map(), etc.
    for x in range(1,DGNS_CD_len):
        if not pd.isna(row['ICD9_DGNS_CD_' + str(x)]): #if there's a nan, continue to the next one
            if row['ICD9_DGNS_CD_' + str(x)] in ICD9_SG_df.index:
                if ICD9_SG_df.loc[row['ICD9_DGNS_CD_' + str(x)]]['Surgical_Proc'] == 1:
                    inpatient_claims_df.loc[index,'Surgical_PRCDR'] = 1
                if ICD9_SG_df.loc[row['ICD9_DGNS_CD_' + str(x)]]['Reop'] == 1:
                    inpatient_claims_df.loc[index,'Reop'] = 1
            if row['ICD9_DGNS_CD_' + str(x)] in ICD9_DG_df.index:
                if ICD9_DG_df.loc[row['ICD9_DGNS_CD_' + str(x)]]['SSI'] == 1:
                    inpatient_claims_df.loc[index,'SSI'] = 1
                if ICD9_DG_df.loc[row['ICD9_DGNS_CD_' + str(x)]]['DVT'] == 1:
                    inpatient_claims_df.loc[index,'DVT'] = 1
            #elif (row['ICD9_DGNS_CD_' + str(x)] not in ICD9_SG_df.index):
                #codes_not_in_ICD9.add(row['ICD9_DGNS_CD_' + str(x)])
    timer += 1
    if timer%50000 == 0:
        print(str(timer) + " rows completed for DG.")
#2850 instances of ICD9 codes in patient claims data but not in obtained ICD9 code files (Many of them repeats of the same code)
#30 unique codes in inpatient files but not in obtained ICD9 codes 

#558 SSI codes found
#120 DVT codes found
#%%

wth = inpatient_claims_df[inpatient_claims_df['SSI'] == 1]


wth2 = inpatient_claims_df[(inpatient_claims_df == '99859').any(axis=1)]
checker_results = 0
for x in range(1,DGNS_CD_len):
    checker_results += (wth[wth['ICD9_DGNS_CD_' + str(x)] == '99859'].shape[0])
for x in range(1,PRCDR_CD_len):
    checker_results += (wth[wth['ICD9_PRCDR_CD_' + str(x)] == '99859'].shape[0])

#%%Output this monstrous dataset to a csv

inpatient_claims_df.to_csv(path_to_files + "Inpatient_Claims_markup_Final.csv",index=False)


#%%Read in CSV
inpatient_claims_df = pd.read_csv(path_to_files + 'Inpatient_Claims_markup_Final.csv')
inpatient_claims_df['CLM_ADMSN_DT'] = pd.to_datetime(inpatient_claims_df['CLM_ADMSN_DT'],format="%Y-%m-%d")
inpatient_claims_df['NCH_BENE_DSCHRG_DT'] = pd.to_datetime(inpatient_claims_df['NCH_BENE_DSCHRG_DT'],format="%Y-%m-%d")



#%% LOS calculation
LOS_list = (inpatient_claims_df['NCH_BENE_DSCHRG_DT'] - inpatient_claims_df['CLM_ADMSN_DT']).apply(lambda x: x.days).tolist()
#from here you could do a rolling average, make a histogram, gather estimators, etc.
#if needed we could also integrate this with below code to collect the date for each LOS calculation
#%%Average LOS
avg = sum(LOS_list)/len(LOS_list)


#%%Readmission, SSI, DVT, reoperation counts 
zero_list_inpatient = [0 for x in range(inpatient_claims_df.shape[0])]
inpatient_claims_df['counted_readmit'],inpatient_claims_df['counted_SSI'],inpatient_claims_df['counted_DVT'],inpatient_claims_df['counted_reop'] = zero_list_inpatient,zero_list_inpatient,zero_list_inpatient,zero_list_inpatient
readmission_tf = 30 #timeframe (in days) for how close to surgery is considered a readmission
SSI_tf = 30 #timeframe (in days) for how close to surgery is considered an SSI
DVT_tf = 30 #timeframe (in days) for how close to surgery is considered a DVT
reop_tf = 3 #timeframe (in days) for how close to surgery is considered a reoperation

tester = []
inpatient_claims_grouped = inpatient_claims_df.groupby('DESYNPUF_ID')
for name,group in inpatient_claims_grouped:
    for index,row in group.iterrows():
        if row['Surgical_PRCDR'] == 1:
            for index2,row2 in group.iterrows():
                time_diff = (row2['CLM_ADMSN_DT'] - row['CLM_ADMSN_DT']).days
                time_diff_readmit = (row2['CLM_ADMSN_DT'] - row['NCH_BENE_DSCHRG_DT']).days
                if row2['counted_readmit'] == 0\
                and time_diff_readmit > 0\
                and time_diff_readmit <= readmission_tf:
                    inpatient_claims_df.loc[index2,'counted_readmit'] = 1
                if row2['SSI'] == 1\
                and row2['counted_SSI'] == 0\
                and time_diff > 0\
                and time_diff <= SSI_tf:
                    tester.append(index2)
                    inpatient_claims_df.loc[index2,'counted_SSI'] = 1
                if row2['DVT'] == 1\
                and row2['counted_DVT'] == 0\
                and time_diff > 0\
                and time_diff <= DVT_tf:
                    inpatient_claims_df.loc[index2,'counted_DVT'] = 1
                if row2['Reop'] == 1\
                and row2['counted_reop'] == 0\
                and time_diff > 0\
                and time_diff <= reop_tf:
                    inpatient_claims_df.loc[index2,'counted_reop'] = 1

#%%Count up results

#For JUST csv 1:
#Total rows (encounters): 66773
#readmissions: 6167
#SSI's:59
#DVT's:9
#average LOS: 5.7 days; maximum value 35 days; minimum is 0

#Total rows (encounters): 1332822
#readmissions: 134069
#SSI's: 22205
#DVT's: 4536
#average LOS: 5.7 days; maximum value 35 days; minimum is 0

#SSI_count: 179107
#DVT: 37261
#reop: 100708

SSI_count = inpatient_claims_df[inpatient_claims_df['counted_SSI'] == 1].shape[0]
DVT_count = inpatient_claims_df[inpatient_claims_df['counted_DVT'] == 1].shape[0]
reop_count = inpatient_claims_df[inpatient_claims_df['counted_reop'] == 1].shape[0]
readmission_count = inpatient_claims_df[inpatient_claims_df['counted_readmit'] == 1].shape[0]

#%%
inpatient_claims_df.to_csv(path_to_files + "Inpatient_Claims_markup_Final_Full.csv")

#%%
code_results = inpatient_claims_df[inpatient_claims_df['Reop'] == 1]

#%%Used to verify SSI and DVT results

#checker_results and code_results should be close; checker_results may be slightly higher since code_results does
#not double count duplicates within a row, but checker_results does
code_results = inpatient_claims_df[inpatient_claims_df['SSI'] == 1]
checker_results = 0
for x in range(1,DGNS_CD_len):
    checker_results += (inpatient_claims_df[inpatient_claims_df['ICD9_DGNS_CD_' + str(x)] == '99859'].shape[0])
for x in range(1,PRCDR_CD_len):
    checker_results += (inpatient_claims_df[inpatient_claims_df['ICD9_PRCDR_CD_' + str(x)] == '99859'].shape[0])



#%%Visualization

import seaborn as sns
import matplotlib.pyplot as plt 
#Visualizations-waiting on other metrics to work before deciding plots 
#Length of Stay 
sns.histplot(LOS_list, binwidth = 3)
plt.title("Length of Stay Distribution")
plt.xlabel("Days");

















