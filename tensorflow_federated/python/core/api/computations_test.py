# Lint as: python3
# Copyright 2018, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for computations.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf

from tensorflow_federated.python.common_libs import test
from tensorflow_federated.python.core.api import computation_types
from tensorflow_federated.python.core.api import computations
from tensorflow_federated.python.core.api import value_base


class ComputationsTest(test.TestCase):

  def test_tf_comp_first_mode_of_usage_as_non_polymorphic_wrapper(self):
    # Wrapping a lambda with a parameter.
    foo = computations.tf_computation(lambda x: x > 10, tf.int32)
    self.assertEqual(str(foo.type_signature), '(int32 -> bool)')
    self.assertEqual(foo(9), False)
    self.assertEqual(foo(11), True)

    # Wrapping an existing Python function with a parameter.
    bar = computations.tf_computation(tf.add, (tf.int32, tf.int32))
    self.assertEqual(str(bar.type_signature), '(<int32,int32> -> int32)')

    # Wrapping a no-parameter lambda.
    baz = computations.tf_computation(lambda: tf.constant(10))
    self.assertEqual(str(baz.type_signature), '( -> int32)')
    self.assertEqual(baz(), 10)

    # Wrapping a no-parameter Python function.
    def bak_fn():
      return tf.constant(10)

    bak = computations.tf_computation(bak_fn)
    self.assertEqual(str(bak.type_signature), '( -> int32)')
    self.assertEqual(bak(), 10)

  def test_tf_fn_with_variable(self):

    @computations.tf_computation
    def read_var():
      v = tf.Variable(10, name='test_var')
      return v

    self.assertEqual(read_var(), 10)

  def test_tf_comp_second_mode_of_usage_as_non_polymorphic_decorator(self):
    # Decorating a Python function with a parameter.
    @computations.tf_computation(tf.int32)
    def foo(x):
      return x > 10

    self.assertEqual(str(foo.type_signature), '(int32 -> bool)')

    self.assertEqual(foo(9), False)
    self.assertEqual(foo(10), False)
    self.assertEqual(foo(11), True)

    # Decorating a no-parameter Python function.
    @computations.tf_computation
    def bar():
      return tf.constant(10)

    self.assertEqual(str(bar.type_signature), '( -> int32)')

    self.assertEqual(bar(), 10)

  def test_tf_comp_with_sequence_inputs_and_outputs_fails(self):
    # This fails right now due to our handling of creation and passing
    # around of tf.data.Datasets; we should be able to define a function
    # like this, but currently it is a limitation.
    with self.assertRaises(ValueError):

      @computations.tf_computation(computation_types.SequenceType(tf.int32))
      def _(x):
        return x

  def test_tf_comp_third_mode_of_usage_as_polymorphic_callable(self):
    # Wrapping a lambda.
    foo = computations.tf_computation(lambda x: x > 0)

    self.assertEqual(foo(-1), False)
    self.assertEqual(foo(0), False)
    self.assertEqual(foo(1), True)

    # Decorating a Python function.
    @computations.tf_computation
    def bar(x, y):
      return x > y

    self.assertEqual(bar(0, 1), False)
    self.assertEqual(bar(1, 0), True)
    self.assertEqual(bar(0, 0), False)

  def test_fed_comp_typical_usage_as_decorator_with_unlabeled_type(self):

    @computations.federated_computation(
        (computation_types.FunctionType(tf.int32, tf.int32), tf.int32))
    def foo(f, x):
      assert isinstance(f, value_base.Value)
      assert isinstance(x, value_base.Value)
      assert str(f.type_signature) == '(int32 -> int32)'
      assert str(x.type_signature) == 'int32'
      result_value = f(f(x))
      assert isinstance(result_value, value_base.Value)
      assert str(result_value.type_signature) == 'int32'
      return result_value

    self.assertEqual(
        str(foo.type_signature), '(<(int32 -> int32),int32> -> int32)')

    @computations.tf_computation(tf.int32)
    def third_power(x):
      return x**3

    self.assertEqual(foo(third_power, 10), int(1e9))
    self.assertEqual(foo(third_power, 1), 1)

  def test_fed_comp_typical_usage_as_decorator_with_labeled_type(self):

    @computations.federated_computation((
        ('f', computation_types.FunctionType(tf.int32, tf.int32)),
        ('x', tf.int32),
    ))
    def foo(f, x):
      return f(f(x))

    @computations.tf_computation(tf.int32)
    def square(x):
      return x**2

    @computations.tf_computation(tf.int32, tf.int32)
    def square_drop_y(x, y):  # pylint: disable=unused-argument
      return x * x

    self.assertEqual(
        str(foo.type_signature), '(<f=(int32 -> int32),x=int32> -> int32)')

    self.assertEqual(foo(square, 10), int(1e4))
    self.assertEqual(square_drop_y(square_drop_y(10, 5), 100), int(1e4))
    self.assertEqual(square_drop_y(square_drop_y(10, 100), 5), int(1e4))
    with self.assertRaisesRegexp(TypeError,
                                 'is not assignable from source type'):
      self.assertEqual(foo(square_drop_y, 10), 100)

  def test_with_tf_datasets(self):

    @computations.tf_computation(computation_types.SequenceType(tf.int64))
    def foo(ds):
      return ds.reduce(np.int64(0), lambda x, y: x + y)

    self.assertEqual(str(foo.type_signature), '(int64* -> int64)')

    @computations.tf_computation
    def bar():
      return tf.data.Dataset.range(10)

    self.assertEqual(str(bar.type_signature), '( -> int64*)')

    self.assertEqual(foo(bar()), 45)

  def test_no_argument_fed_comp(self):

    @computations.federated_computation
    def foo():
      return 10

    self.assertEqual(str(foo.type_signature), '( -> int32)')
    self.assertEqual(foo(), 10)


if __name__ == '__main__':
  test.main()
