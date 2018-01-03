import sys; import os
sys.path.append(os.path.abspath("./"))
from helper import Utilities, PerformanceEvaluation
import pandas as pd
import numpy as np
from metric_learning import MetricLearning, Subsampling
from user_feedback import Similarity
import pickle
from scipy.misc import comb
import time
from deep_metric_learning import Deep_Metric
from deep import Deep_Metric1
"""
In the demo, we will showcase an example of special purpose publication.
The data user wants the published energy database to maximally retain the information about peak-time energy usage
"""

# Initialization of some useful classes
util = Utilities()
pe = PerformanceEvaluation()
mel = MetricLearning()

# step 1: get the database to be published
day_profile = pd.read_pickle('dataset/dataframe_all_energy.pkl')
# day_profile = day_profile.iloc[0:90,0::4] # subsample the database to improve the speed for demonstration purpose
day_profile = day_profile.iloc[:90,0::4] # subsample the database to improve the speed for demonstration purpose
day_profile.index = range(len(day_profile.index))
rep_mode = 'mean'
anonymity_level = 5 # desired anonymity level

# step 2: data user specifies his/her interest. In the example, the data user is interested in preserving the
# information of the cumulative energy use during peak time. In this case, he/she would also need to specify the
# starting and ending time of the peak usage time
interest = 'window-usage'
window = [17,21]

# step 3: pre-sanitize the database
sanitized_profile_baseline = util.sanitize_data(day_profile, distance_metric='euclidean',
                                                    anonymity_level=anonymity_level,rep_mode = rep_mode,
                                                    window=window)
loss_generic_metric = pe.get_statistics_loss(data_gt=day_profile, data_sanitized=sanitized_profile_baseline,
                                                         mode=interest,window=window)
print("information loss with learned metric %s" % loss_generic_metric)

df_subsampled_from = sanitized_profile_baseline.drop_duplicates().sample(frac=1)
subsample_size_max = int(comb(len(df_subsampled_from),2))
print('total number of pairs is %s' % subsample_size_max)

# step 4: sample a subset of pre-sanitized database and form the data points into pairs
subsample_size = int(round(subsample_size_max/2))
sp = Subsampling(data=df_subsampled_from)
data_pair = sp.uniform_sampling(subsample_size=subsample_size)

# User receives the data pairs and label the similarity
sim = Similarity(data=data_pair)
sim.extract_interested_attribute(interest='statistics', stat_type=interest,window=window)
similarity_label, data_subsample = sim.label_via_silhouette_analysis(range_n_clusters=range(2,8))

# step 5: PAD learns a distance metric that represents the interest of the user from the labeled data pairs
dm = Deep_Metric()
dm.train(data_pair, similarity_label)

# step 6: the original database is privatized using the learned metric
sanitized_profile_deep = util.sanitize_data(day_profile, distance_metric="deep",anonymity_level=anonymity_level,
                                       rep_mode=rep_mode, deep_model=dm, window=window)

# (optionally for evaluation purpose) Evaluating the information loss of the sanitized database
loss_learned_metric_deep = pe.get_information_loss(data_gt=day_profile,
                                              data_sanitized=sanitized_profile_deep.round(),
                                              window=window)

print("sampled size %s" % subsample_size)
# print("information loss with learned metric deep %s, %s and %s" % (loss_learned_metric_deep, loss_learned_metric_deeps, loss_learned_metric))
print("information loss with learned metric deep %s" % (loss_learned_metric_deep))
