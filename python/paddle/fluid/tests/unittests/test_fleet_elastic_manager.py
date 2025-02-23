#   Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import os
import time
import unittest
import argparse

from paddle.distributed.fleet.elastic.manager import ElasticManager
from paddle.distributed.fleet.elastic.manager import ELASTIC_TIMEOUT


class MockLease():
    def refresh(self):
        pass


class MockEtcdClient:
    def __init__(self, lease=None):
        self._lease = lease

    def put(self, key, value, lease=None):
        pass

    def get(self, key):
        value = "0"
        return value, value

    def delete_prefix(self, key):
        pass

    def get_prefix(self, key_prefix):
        hosts = ["10.10.10.1:6001", "10.10.10.2:6001"]
        return hosts

    def add_watch_callback(self, *args, **kwargs):
        return "host_watch"

    def add_watch_prefix_callback(self, key_prefix, callback, **kwargs):
        callback(None)
        return "host_watch"

    def cancel_watch(self, watch_id):
        pass

    def delete(self, key):
        pass

    def lease(self, ttl):
        if self._lease:
            return self._lease
        else:
            return MockLease()


class TestElasticManager(unittest.TestCase):
    def setUp(self):
        self.etcd_client = MockEtcdClient()

    def test_elastic_manager_init(self):
        class Argument:
            elastic_server = "127.0.0.1:2379"
            job_id = "test_job_id_123"
            np = "2"
            gpus = "0"
            nproc_per_node = 1
            host = None
            host_port = None
            scale = None
            force = None
            backend = 'gloo'

        args = Argument()

        class _MockLease():
            def refresh(self):
                raise ValueError("valid error, this only for unittest")

        etcd_client = MockEtcdClient(lease=_MockLease())
        elastic = ElasticManager(args, etcd_client=etcd_client)

    def test_match_faulttolerance(self):
        class Argument:
            elastic_server = "127.0.0.1:2379"
            job_id = "test_job_id_123"
            np = "2"
            gpus = "0"
            nproc_per_node = 1
            host = None
            host_port = None
            scale = None
            force = None
            backend = 'gloo'

        args = Argument()
        elastic = ElasticManager(args, self.etcd_client)
        hosts = ["10.10.10.1:6001", "10.10.10.2:6001"]
        os.environ[
            'PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001"
        self.assertEqual(elastic._match(hosts), True)
        hosts = ["10.10.10.1:6001"]
        os.environ['PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.1:6001"
        self.assertEqual(elastic._match(hosts), False)

    def test_match_elastic(self):
        class Argument:
            elastic_server = "127.0.0.1:2379"
            job_id = "test_job_id_123"
            np = "2:4"
            gpus = "0"
            nproc_per_node = 1
            host = None
            host_port = None
            scale = None
            force = None
            backend = 'gloo'

        os.environ['PADDLE_ELASTIC_TIMEOUT'] = "60"
        args = Argument()
        os.environ['FLAGS_START_PORT'] = "6001"
        os.environ[
            'DISTRIBUTED_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001,10.10.10.3:6001,10.10.10.4:6001"
        os.environ[
            'PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001,10.10.10.3:6001,10.10.10.4:6001"
        elastic = ElasticManager(args, self.etcd_client)
        hosts = ["10.10.10.1:6001", "10.10.10.2:6001"]
        self.assertEqual(elastic._match(hosts), False)

        hosts = [
            "10.10.10.1:6001", "10.10.10.2:6001", "10.10.10.3:6001",
            "10.10.10.4:6001"
        ]
        self.assertEqual(elastic._match(hosts), True)

        hosts = ["10.10.10.1:6001", "10.10.10.2:6001", "10.10.10.3:6001"]
        self.assertEqual(elastic._match(hosts), False)

        hosts = ["10.10.10.1:6001"]
        self.assertEqual(elastic._match(hosts), False)

        os.environ[
            'DISTRIBUTED_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001"
        os.environ[
            'PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001"
        elastic = ElasticManager(args, self.etcd_client)
        hosts = ["10.10.10.1:6001", "10.10.10.2:6001"]
        self.assertEqual(elastic._match(hosts), True)

        # TODO test timeout
        #time.sleep(60)
        #self.assertEqual(elastic._match(hosts), True)

    def test_update_hosts_for_faulttolerance(self):
        class Argument:
            elastic_server = "127.0.0.1:2379"
            job_id = "test_job_id_123"
            np = "0"
            gpus = "0"
            nproc_per_node = 1
            host = None
            host_port = None
            scale = None
            force = None
            backend = 'gloo'

        args = Argument()
        os.environ['FLAGS_START_PORT'] = "6001"
        os.environ['PADDLE_ELASTIC_NP'] = "2"
        os.environ['PADDLE_TRAINERS'] = "10.10.10.1,10.10.10.2"
        os.environ[
            'DISTRIBUTED_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001"
        os.environ[
            'PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001"
        elastic = ElasticManager(args, self.etcd_client)
        # add 10.10.10.3:6001
        os.environ['PADDLE_TRAINER_ID'] = "0"
        elastic.host_port = "10.10.10.1:6001"
        elastic.hosts = ["10.10.10.1:6001", "10.10.10.2:6001"]
        elastic._update_hosts()
        self.assertEqual(os.getenv('PADDLE_TRAINERS'), "10.10.10.1,10.10.10.2")

        # add 10.10.10.3:6001
        elastic.host_port = "10.10.10.3:6001"
        elastic.hosts = ["10.10.10.1:6001", "10.10.10.3:6001"]
        os.environ['PADDLE_TRAINER_ID'] = "1"
        elastic._update_hosts()
        self.assertEqual(os.getenv('PADDLE_TRAINERS'), "10.10.10.1,10.10.10.3")

        elastic.host_port = "10.10.10.3:6001"
        elastic.hosts = ["10.10.10.1:6001", "10.10.10.3:6001"]
        os.environ['PADDLE_TRAINER_ID'] = "-1"
        elastic._update_hosts()
        self.assertEqual(os.getenv('PADDLE_TRAINERS'), "10.10.10.1,10.10.10.3")

    def test_update_hosts_for_elastic(self):
        #######################
        #  elastic, scale up  #
        #######################
        class Argument:
            elastic_server = "127.0.0.1:2379"
            job_id = "test_job_id_123"
            np = "2:4"
            gpus = "0"
            nproc_per_node = 1
            host = None
            host_port = None
            scale = None
            force = None
            backend = 'gloo'

        args = Argument()

        os.environ['FLAGS_START_PORT'] = "6001"
        os.environ['PADDLE_TRAINERS'] = "10.10.10.1,10.10.10.2"
        os.environ[
            'DISTRIBUTED_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001"
        os.environ[
            'PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.2:6001"
        elastic = ElasticManager(args, self.etcd_client)
        # add 10.10.10.3:6001
        elastic.host_port = "10.10.10.1:6001"
        elastic.hosts = [
            "10.10.10.1:6001", "10.10.10.2:6001", "10.10.10.3:6001"
        ]
        elastic._update_hosts()
        #self.assertEqual(elastic.all_host_endpoints,
        #                 ["10.10.10.1:6001", "10.10.10.2:6001", "10.10.10.3:6001"])
        self.assertEqual(
            os.getenv('PADDLE_TRAINERS'), "10.10.10.1,10.10.10.2,10.10.10.3")

        #######################
        # elastic, scale down #
        #######################
        os.environ[
            'PADDLE_TRAINERS'] = "10.10.10.0,10.10.10.1,10.10.10.2,10.10.10.3"
        os.environ[
            'DISTRIBUTED_TRAINER_ENDPOINTS'] = "10.10.10.0:6000,10.10.10.1:6001,10.10.10.2:6001,10.10.10.3:6001"
        os.environ[
            'PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.0:6000,10.10.10.1:6001,10.10.10.2:6001,10.10.10.3:6001"
        elastic = ElasticManager(args, self.etcd_client)
        # remove 10.10.10.1:6001
        elastic.host_port = "10.10.10.1:6001"
        elastic.hosts = [
            "10.10.10.1:6001", "10.10.10.2:6001", "10.10.10.3:6001"
        ]
        elastic._update_hosts()
        #self.assertEqual(elastic.all_host_endpoints,
        #                 ["10.10.10.3:6001", "10.10.10.1:6001", "10.10.10.2:6001"])
        self.assertEqual(
            os.getenv('PADDLE_TRAINERS'), "10.10.10.3,10.10.10.1,10.10.10.2")
        self.assertEqual(
            os.getenv('DISTRIBUTED_TRAINER_ENDPOINTS'),
            "10.10.10.3:6001,10.10.10.1:6001,10.10.10.2:6001")

        ############
        os.environ['PADDLE_TRAINERS'] = "10.10.10.1,10.10.10.1"
        os.environ[
            'DISTRIBUTED_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.1:6002,10.10.10.1:6003,10.10.10.1:6004"
        os.environ[
            'PADDLE_TRAINER_ENDPOINTS'] = "10.10.10.1:6001,10.10.10.1:6002,10.10.10.1:6003,10.10.10.1:6004"
        elastic = ElasticManager(args, self.etcd_client)
        # remove 10.10.10.1:6001
        elastic.host_port = "10.10.10.1:6001"
        os.environ['PADDLE_TRAINER_ID'] = "-1"
        elastic.hosts = ["10.10.10.1:6001", "10.10.10.1:6001"]
        elastic._update_hosts()
        #self.assertEqual(elastic.all_host_endpoints,
        #                 ["10.10.10.1:6001", "10.10.10.1:6001"])
        self.assertEqual(os.getenv('PADDLE_TRAINERS'), "10.10.10.1,10.10.10.1")
        self.assertEqual(
            os.getenv('DISTRIBUTED_TRAINER_ENDPOINTS'),
            "10.10.10.1:6001,10.10.10.1:6001")

    def test_exit(self):
        class Argument:
            elastic_server = "127.0.0.1:2379"
            job_id = "test_job_id_123"
            np = "2"
            gpus = "0"
            nproc_per_node = 1
            host = None
            host_port = None
            scale = None
            force = None
            backend = 'gloo'

        args = Argument()
        elastic = ElasticManager(args, self.etcd_client)
        elastic.exit()


if __name__ == "__main__":
    unittest.main()
