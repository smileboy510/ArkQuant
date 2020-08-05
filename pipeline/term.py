# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import glob,numpy as np
from weakref import WeakValueDictionary


class NotSpecific(Exception):

    def __str__(self):
        return ('object not specific')

    __repr__ = __str__()


class Term(object):
    """
        term.specialize(domain)
        执行算法 --- 拓扑结构
        退出算法 --- 裁决模块
        Dependency-Graph representation of Pipeline API terms.
        结构:
            1 节点 --- 算法，基于拓扑结构 --- 实现算法逻辑 表明算法的组合方式
            2 不同的节点已经应该继承相同的接口，不需要区分pipeline还是featureUnion
            3 同一层级的不同节点相互独立，一旦有连接不同层级
            4 同一层级节点计算的标的集合交集得出下一层级的输入，不同节点之间不考虑权重分配因为交集（存在所有节点）
            5 每一个节点产生有序的股票集合，一层所有的交集按照各自节点形成综合排序
            6 最终节点 --- 返回一个有序有限的集合
        节点:
            1 inputs --- asset list
            2 compute ---- algorithm list
            3 outputs --- algorithm list & asset list
    """
    default_input = NotSpecific
    _term_cache = WeakValueDictionary

    namespace = dict()

    __slots__ = ['domain','dtype','term_logic','_subclass_called_validate']

    def __new__(cls,
                domain,
                script,
                params,
                dtype = None
                ):

        dtype = dtype if dtype else list()

        script_path= glob.glob('strategy/%s.py'%script)
        with open(script_path, 'r') as f:
            exec(f.read(), cls.namespace)
        logic_cls = cls.namespace[script]
        identity = cls._static_identity(domain,logic_cls,params,dtype)

        try:
            return cls._term_cache[identity]
        except KeyError:
            new_instance = cls._term_cache[identity] = \
                super(Term,cls).__new__(cls)._init(domain,logic_cls,params,dtype)
            return new_instance

    @classmethod
    def _static_identity(cls,domain,script_class,script_params,dtype):
        return domain,script_class,script_params,dtype

    def _init(self, domain,script,params,dtype):
        """
            __new__已经初始化后，不需要在__init__里面调用
            Noop constructor to play nicely with our caching __new__.  Subclasses
            should implement _init instead of this method.

            When a class' __new__ returns an instance of that class, Python will
            automatically call __init__ on the object, even if a new object wasn't
            actually constructed.  Because we memoize instances, we often return an
            object that was already initialized from __new__, in which case we
            don't want to call __init__ again.

            Subclasses that need to initialize new instances should override _init,
            which is guaranteed to be called only once.
            Parameters
            ----------
            domain : zipline.pipeline.domain.Domain
                The domain of this term.
            dtype : np.dtype
                Dtype of this term's output.
            params : tuple[(str, hashable)]
                Tuple of key/value pairs of additional parameters.
        """
        self.domain = domain
        self.dtype = dtype
        try:
            instance = script(params)
            self.term_logic = instance
            self._validate()
        except TypeError:
            self._subclass_called_validate = False

        assert self._subclass_called_super_validate, (
            "Term._validate() was not called.\n"
            "This probably means that logic cannot be initialized."
        )
        del self._subclass_called_super_validate

        return self

    def _validate(self):
        """
        Assert that this term is well-formed.  This should be called exactly
        once, at the end of Term._init().
        """
        # mark that we got here to enforce that subclasses overriding _validate
        # call super().
        self._subclass_called_super_validate = True

    @property
    def dependencies(self):
        """
        A dictionary mapping terms that must be computed before `self` to the
        number of extra rows needed for those terms.
        """
        return self.default_input

    @dependencies.setter
    def dependencies(self,terms):
        for item in terms:
            if not isinstance(item,self):
                raise TypeError('dependencies must be Term')
        return terms

    def postprocess(self,data):
        """
            called with an result of self ,after any user-defined screens have been applied
            this is mostly useful for transforming  the dtype of an output
        """
        if self.dtype == bool:
            if not isinstance(data,self.dtype):
                raise TypeError('style of data is not %s' % self.dtype)
            return data
        else:
            try:
                data = self.dtype(data)
            except Exception as e:
                raise TypeError('cannot transform the style of data to %s due to error %s' % (self.dtype, e))
            return data

    def _compute(self,inputs,data):
        """
            inner method
            1. subclass should implement when _verify_asset_finder is True
            2. self.postprocess()
        """
        output = self.term_logic.compute(inputs,data)
        validate_output = self.postprocess(output)
        return validate_output

    def compute(self,inputs,data):
        """
            1. subclass should implement when _verify_asset_finder is True
            2. self.postprocess()
        """
        output = self._compute(inputs,data)
        return output

    def recursive_repr(self):
        """A short repr to use when recursively rendering terms with inputs.
        """
        # Default recursive_repr is just the name of the type.
        return type(self).__name__
