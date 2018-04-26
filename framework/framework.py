from framework.similarity.simularatielist import SimularatieList
from framework.similarity.similarity import Similarity
from framework.models.kward import K_ward
from .metric_learning.linearmetric import *
from .metric_learning.nonlineardeepmetric import *
# from framework.metric_learning.basemetriclearning import BasemetricLearning
# from framework.metric_learning.linearmetric import Linear_Metric
# from framework.metric_learning.nonlineardeepmetric import NonlinearDeepMetric
from scipy.misc import comb
from framework.utilities.outputgroupper import OutputGroupper
from framework.utilities.datadescriptor import DataDescriptorMetadata, DataDescriptorBase, DataDescriptorTimeSerice
from framework.similarity.basesimularity import BaseSimularity
from framework.utilities.resampler import Resampler, Subsampling
from framework.utilities.configverify import Verifyerror
import math
import copy
from itertools import chain
import pandas as pd
import sys
import inspect
import random

class Framwork:
    def __init__(self, data, anonymity_level=5,dataset_description=None, seed=None,rep_mode = "mean",min_resample_factor = 5):
        self.data = data
        self._simularatie_list = SimularatieList()
        self.data_descriptors = []
        self.anonymity_level = anonymity_level
        self.subsampling = None
        self.similarity = None
        self.dataset_description = dataset_description
        self.data_has_been_resample_data_into_blocks_of_output_rate = False
        self.amount_of_sensors =None
        self.rep_mode  = rep_mode
        self._resampler = Resampler()
        self.max_clusters = 8
        self.min_resample_factor = min_resample_factor
        self.seed = seed

    def _get_data_for_sanitize(self):
        output_data = pd.DataFrame()
        for dd in self.data_descriptors:
            if not isinstance(dd, DataDescriptorMetadata):
                output_data = pd.concat([output_data,self.data.iloc[:,dd.data_start_index:dd.data_end_index+1]], axis=1)
        return output_data

    def _get_data_for_model_optimazation(self):
        output_data = self._get_data_for_sanitize()
        output_data = output_data.sample(math.floor(len(output_data.index)/10))
        return output_data

    def _add_metadata_for_sanitize_data(self,sanitize_data):
        output_data = pd.DataFrame()
        for dd in self.data_descriptors:
            if isinstance(dd, DataDescriptorMetadata):
                output_data = pd.concat([output_data,self.data.iloc[:,dd.data_start_index:dd.data_end_index+1]], axis=1)
        output_data = pd.concat([output_data,sanitize_data], axis=1)
        return output_data

    def _can_ensure_k_anonymity(self,anonymity_level,amount_of_inputs):
        if (2*anonymity_level-1)*5<amount_of_inputs:
            return True
        return False

    def _find_max_k(self,amount_of_inputs):
        return math.floor((amount_of_inputs+5)/10)

    def add_meta_data(self,data_descriptor):
        if isinstance(data_descriptor, DataDescriptorMetadata):
            self.data_descriptors.append(data_descriptor)

    def add_simularatie(self,simularatie):
        # if isinstance(simularatie, BaseSimularity):
        self._simularatie_list.add_simularatie(simularatie)
            # if isinstance(simularatie.data_descriptor, DataDescriptorBase):
        self.data_descriptors.append(simularatie.data_descriptor)

    def _find_Simularaty(self):
        # TODO: make my
        raise NotImplementedError('NotImplemented')

    def _find_all_Metric_Leanings(self):
        metrics = []
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj):
                if "framework.metric_learning" in str(obj):
                    if obj is Linear_Metric:
                        metrics.append(obj)
                    elif issubclass(obj, BasemetricLearning) and obj is not BasemetricLearning:
                        metrics.append(obj)
        return metrics

    def _find_Metric_Leaning(self,data_pair,similarity_label, subsample):
        metricNames = self._find_all_Metric_Leanings()
        metricesResults = []
        metrics = []
        for metric in metricNames:
            metric = metric()
            metrics.append(metric)
            TestLoss = metric.train(data_pair, similarity_label)
            final_sanitized_data = self._sanitize_data(data = subsample, distance_metric_type="metric",
                        anonymity_level=self.anonymity_level,metric=metric, rep_mode = self.rep_mode)
            loss_metric=  self._simularatie_list.get_statistics_loss(subsample,final_sanitized_data)
            metricesResults.append(loss_metric)
        # nonlm = NonlinearDeepMetric()
        # nonlm.train(data_pair, similarity_label)
        best_model_index =  metricesResults.index(min(metricesResults))
        return metrics[best_model_index]

    def _find_Model(self, data):
        # TODO: make my
        raise NotImplementedError('NotImplemented')

    def _subsample(self,presenitizedData, sub_sampling_size=0.1, subsampleTrys = 0, seed=None):
        if subsampleTrys > 5:
            raise ValueError("The data is to simuler to be sanitezed")
        self.subsampling = Subsampling(presenitizedData.sample(frac=sub_sampling_size))
        subsample_size_max = int(comb(len(self.subsampling.data), 2))
        print('total number of pairs is %s' % subsample_size_max)
        data_pair_all, data_pair_all_index = self.subsampling.uniform_sampling(subsample_size=subsample_size_max, seed=seed)
        self.similarity = Similarity(data=data_pair_all)
        self.similarity.extract_interested_attribute(self._simularatie_list.simularaties)
        if len(self.similarity.data_interested) < self.max_clusters:
            self.max_clusters = len(self.similarity.data_interested)
        similarity_label, data_subsample = self.similarity.label_via_silhouette_analysis(range_n_clusters=range(2,self.max_clusters), seed=self.seed)
        if similarity_label == []:
            return self._subsample(presenitizedData, sub_sampling_size=sub_sampling_size+0.1, subsampleTrys = subsampleTrys+1, seed=seed)
        else:
            # similarity_label_all_series = pd.Series(similarity_label)
            # similarity_label_all_series.index = data_pair_all_index
            print('similarity balance is %s'% [sum(similarity_label),len(similarity_label)])
        return similarity_label, data_pair_all

    def _presanitized(self):
        sanitized_df = self._sanitize_data(data=self._get_data_for_sanitize(), distance_metric_type="init", rep_mode = self.rep_mode,
                        anonymity_level=self.anonymity_level)
        loss_presenitized=  self._simularatie_list.get_statistics_loss(self._get_data_for_sanitize(),sanitized_df)
        print("information loss with presenitized %s" % loss_presenitized)
        print("amount of samples presenitized_data  %s" % len(sanitized_df))
        return sanitized_df

    def _sanitize_data(self,distance_metric_type , anonymity_level, data, rep_mode, **kwargs):
        k_ward = None
        if distance_metric_type == "init":
            k_ward = K_ward(data, rep_mode = rep_mode ,k=anonymity_level, metric=self._simularatie_list)
        else:
            metric = kwargs["metric"]
            k_ward = K_ward(data, rep_mode = rep_mode,k=anonymity_level, metric=metric)
        k_ward.find_clusters()
        groups = k_ward.get_groups()

        sanitized_df = pd.DataFrame()
        for group in groups:
            # group.rep_mode = "max"
            # group.get_rep()
            sanitized_value = group.rep.to_frame().transpose()
            keys = group.get_member_ids()
            for key in keys:
                sanitized_value.index = [key]
                sanitized_df = sanitized_df.append(sanitized_value)
        sanitized_df.columns = data.columns
        return sanitized_df


    def generated_data_description(self):
        dd_string_out = []
        if self.dataset_description is not None:
            dd_string_out.append(self.dataset_description)
        for data_descriptor in self.data_descriptors:
            dd_string_out.append(data_descriptor.get_str_description())
        return '\n'.join(dd_string_out)

    def change_anonymity_level(self,resample_factor):
        amount_of_data_slices = len(self.data.index)
        max_k = self._find_max_k(amount_of_data_slices)
        if max_k > self.anonymity_level * self.amount_of_sensors:
            self.anonymity_level = self.anonymity_level * self.amount_of_sensors
        else:
            self.anonymity_level = max_k
        print('anonymity_level set to: ' + str(self.anonymity_level))

    def run(self):
        self.data = Verifyerror().verify(self.data, self._simularatie_list, self.data_descriptors)
        self.amount_of_sensors = len(self.data.index)
        _can_ensure_k_anonymity = self._can_ensure_k_anonymity(self.anonymity_level, self.amount_of_sensors)
        if not _can_ensure_k_anonymity:
            self.data, self._simularatie_list, self.data_descriptors, resample_factor = self._resampler.resample_data_into_blocks(self.data, self.data_descriptors, self._simularatie_list, self.min_resample_factor)
            Verifyerror().verify_efter_can_not_ensure_k_anonymity(self.data, self._simularatie_list)
            self.change_anonymity_level(resample_factor)
            print("amount of samples after spilt %s" % len(self.data.index))
            print("amount of columns after spilt %s" % len(self.data.columns))

        presenitized_data = self._presanitized()

        similarity_label, data_pair = self._subsample(presenitized_data,seed=self.seed)

        model = self._find_Metric_Leaning(data_pair,similarity_label, self._get_data_for_model_optimazation())

        final_sanitized_data = self._sanitize_data(data = self._get_data_for_sanitize(), distance_metric_type="metric",
                        anonymity_level=self.anonymity_level,metric=model, rep_mode = self.rep_mode)
        loss_metric=  self._simularatie_list.get_statistics_loss(self._get_data_for_sanitize(),final_sanitized_data)
        print("information loss with nonlm metric %s" % loss_metric)

        # lm = Linear_Metric()
        # lm.train(data_pair, similarity_label)
        # final_sanitized_data = self._sanitize_data(data = self._get_data_for_sanitize(), distance_metric_type="metric", rep_mode = "mean",
        #                 anonymity_level=self.anonymity_level,metric=lm)
        # loss_metric=  self._simularatie_list.get_statistics_loss(self._get_data_for_sanitize(),final_sanitized_data)
        # print("information loss with Linear_Metric metric %s" % loss_metric)

        if not _can_ensure_k_anonymity:
            transformed_data, self._simularatie_list, self.data_descriptors = self._resampler.create_timeserices_from_slices_of_data(final_sanitized_data, self._simularatie_list, self.amount_of_sensors)
            transformed_data, self.data_descriptors = OutputGroupper(self.data_descriptors).transform_data(transformed_data)
        else:
            transformed_data, self.data_descriptors = OutputGroupper(self.data_descriptors).transform_data(self._add_metadata_for_sanitize_data(final_sanitized_data))
        return transformed_data.sort_index(), loss_metric, self.anonymity_level