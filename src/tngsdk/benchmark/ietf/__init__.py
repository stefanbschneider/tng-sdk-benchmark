#  Copyright (c) 2018 SONATA-NFV, 5GTANGO, Paderborn University
# ALL RIGHTS RESERVED.
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
#
# Neither the name of the SONATA-NFV, 5GTANGO, Paderborn University
# nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written
# permission.
#
# This work has been performed in the framework of the SONATA project,
# funded by the European Commission under Grant number 671517 through
# the Horizon 2020 and 5G-PPP programmes. The authors would like to
# acknowledge the contributions of their colleagues of the SONATA
# partner consortium (www.sonata-nfv.eu).
#
# This work has also been performed in the framework of the 5GTANGO project,
# funded by the European Commission under Grant number 761493 through
# the Horizon 2020 and 5G-PPP programmes. The authors would like to
# acknowledge the contributions of their colleagues of the SONATA
# partner consortium (www.5gtango.eu).
import os
import yaml
import json
from tngsdk.benchmark.helper import ensure_dir
from tngsdk.benchmark.logger import TangoLogger
from tngsdk.benchmark.ietf.vnf_bd import vnf_bd as VNF_BD_Model
import pyangbind.lib.pybindJSON as pybindJSON


LOG = TangoLogger.getLogger(__name__)


class IetfBmwgVnfBD_Generator(object):

    def __init__(self, args, service_experiments):
        self.args = args
        # check inputs and possibly skip
        if self.args.ibbd_dir is None:
            return
        self.service_experiments = service_experiments

    def run(self):
        # check inputs and possibly skip
        if self.args.ibbd_dir is None:
            LOG.info("IETF BMWG BD dir not specified (--ibbd). Skipping.")
            return
        # generate IETF BMWG BD, PP, BR
        for ex_id, ex in enumerate(self.service_experiments):
            # iterate over all experiment configurations
            for _, ec in enumerate(ex.experiment_configurations):
                # generate assets
                try:
                    bd_path = self._generate_bd(ex_id, ec)
                    LOG.debug("Generated IETF BMWG BD: {}".format(bd_path))
                except BaseException as exx:
                    LOG.error("Could not generate IETF VNF BD for EC: {}\n{}"
                              .format(ec, exx))

    def _find_vnf_id(self, vnf_name, nsd):
        """
        Get the VNF ID defined in the NSD by using the VNF name.
        """
        for f in nsd.get("network_functions"):
            if f.get("vnf_name") == vnf_name:
                return f.get("vnf_id")
        return vnf_name

    def _generate_bd(self, ex_id, ec):
        # instantiate model
        m = VNF_BD_Model()
        # output path for YAML file
        bd_path = os.path.join(self.args.ibbd_dir,
                               "{}-bd.yaml".format(ec.name))
        # populate the model with the actual data
        # (always assing strings, assigning ints does not work,
        # types seem to be automaticall converted by the model)
        # 1. header section
        m.vnf_bd.id = "{:05d}".format(ec.run_id)
        m.vnf_bd.name = ec.name
        m.vnf_bd.version = "0.1"
        m.vnf_bd.author = "tng-bench"
        m.vnf_bd.description = ("BD generated by"
                                + " tng-bench (https://sndzoo.github.io/).")
        # 2. experiments section
        m.vnf_bd.experiments.methods = str(ex_id)
        m.vnf_bd.experiments.tests = str(
            ec.parameter.get("ep::header::all::config_id", -1))
        m.vnf_bd.experiments.trials = str(
            ec.parameter.get("ep::header::all::repetition", -1))
        # 3. environment section
        m.vnf_bd.environment.name = self.args.config.get(
            "targets")[0].get("name")
        m.vnf_bd.environment.description = self.args.config.get(
            "targets")[0].get("description")
        m.vnf_bd.environment.plugin.type = self.args.config.get(
            "targets")[0].get("pdriver")
        p1 = m.vnf_bd.environment.plugin.parameters.add("entrypoint")
        p1.value = self.args.config.get(
            "targets")[0].get("pdriver_config").get("host")
        # 4. targets section
        t1 = m.vnf_bd.targets.add("01")
        t1.author = ec.experiment.target.get("vendor")
        t1.name = ec.experiment.target.get("name")
        t1.version = ec.experiment.target.get("version")
        # 5. scenario section
        # 5.1. nodes
        if ec.vnfds is not None:
            for path, vnfd in ec.vnfds.items():
                if "mp." in vnfd.get("name"):
                    nid = vnfd.get("name")
                    short_nid = nid
                else:
                    # full tripple nid
                    nid = "{}.{}.{}".format(
                        vnfd.get("vendor"),
                        vnfd.get("name"),
                        vnfd.get("version"))
                    # short vnf_id defined in NSD
                    if ec.nsd is not None:
                        short_nid = self._find_vnf_id(vnfd.get("name"), ec.nsd)
                    else:
                        short_nid = nid
                n1 = m.vnf_bd.scenario.nodes.add(nid)
                n1.type = "external"  # tng-bench always uses external ones?
                # attention: assumes single VDU
                vdu = vnfd.get("virtual_deployment_units")[0]
                n1.image = vdu.get("vm_image")
                n1.image_format = vdu.get("vm_image_format")
                # 5.1.1. resources
                res = vdu.get("resource_requirements")
                if res.get("cpu").get("vcpus"):
                    n1.resources.cpu.vcpus = str(res.get("cpu").get("vcpus"))
                if res.get("cpu").get("cpu_bw"):
                    n1.resources.cpu.cpu_bw = str(res.get("cpu").get("cpu_bw"))
                if res.get("cpu").get("vcpus"):
                    n1.resources.cpu.pinning = str(res.get("cpu").get("vcpus"))
                if res.get("memory").get("size"):
                    n1.resources.memory.size = str(res.get("memory").get("size"))
                if res.get("memory").get("size_unit"):
                    n1.resources.memory.unit = str(res.get("memory").get("size_unit"))
                if res.get("storage").get("size"):
                    n1.resources.storage.size = str(res.get("storage").get("size"))
                if res.get("storage").get("size_unit"):
                    n1.resources.storage.unit = str(res.get("storage").get("size_unit"))
                n1.resources.storage.volumes = None # not supported
                # 5.1.2. connection points
                for cp in vnfd.get("connection_points", []):
                    # build connection point id: node_id:cp_id
                    cp_id = "{}:{}".format(short_nid, cp.get("id"))
                    cpnew = n1.connection_points.add(cp_id)
                    cpnew.interface = cp.get("interface")
                    cpnew.type = cp.get("type")
                # 5.1.3. lifecycle
                # tng-bench only has two lifecycle events: start and stop
                lc_start = n1.lifecycle.add("start")
                # tng-bench does not support parameters
                lc_start.implementation = ec.parameter.get("ep::function::{}::cmd_start".format(nid), "")  # fill with cmd_start
                lc_stop = n1.lifecycle.add("stop")
                lc_stop.implementation = ec.parameter.get("ep::function::{}::cmd_stop".format(nid), "")  # fill with cmd_start
        # 5.2. links
        if ec.nsd is not None:
            for l in ec.nsd.get("virtual_links"):
                lnew = m.vnf_bd.scenario.links.add(l.get("id"))
                lnew.type = l.get("connectivity_type")
                for cpr in l.get("connection_points_reference"):
                    lnew.connection_point_refs.append(cpr)
        # 6. proceedings section
        # 6.1. attributes
        at_dur = m.vnf_bd.proceedings.attributes.add("duration")
        at_dur.value = str(ec.parameter.get("ep::header::all::time_limit"))
        # TODO: 6.2 agents
        #ag1 = m.vnf_bd.proceedings.agents.add("01")
        # TODO: 6.3 monitors
        #mo1 = m.vnf_bd.proceedings.monitors.add("01")

        # render BD using template
        bd_str_json = pybindJSON.dumps(m, mode="ietf")  # serialize
        bd_str = yaml.dump(json.loads(bd_str_json))  # translate json to yaml
        print(bd_str)
        print("---")
        # print((ec.parameter))
        # print("--- NSD")
        # print((ec.nsd))
        # print("----")
        # print(self.args.config)
        # write BD
        ensure_dir(bd_path)
        with open(bd_path, "w") as f:
            f.write(bd_str)
        return bd_path

    def _get_ep_from_ec(self, ec, node, ep_name):
        """
        Helper that get resource limit from flat
        parameter list of an EC.
        """
        for k in ec.parameter.keys():
            # fuzzy matchin using "in" statement
            if node in k and ep_name in k:
                return ec.parameter.get(k)
        LOG.warning("Could not find resource limit for node: {}"
                    .format(node))
        return None
