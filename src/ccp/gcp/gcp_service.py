import re
import traceback
import uuid
from cloudshell.cp.core.models import *
import googleapiclient.discovery
import os
from wait_operations import *


class GCPService:
    def __init__(self, project, json_cred_path, logger=None):
        self.project = project
        self.logger = logger
        self.client = None
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_cred_path

        pass

    def _get_client(self):
        if self.client:
            return self.client

        self.client = googleapiclient.discovery.build('compute', 'v1')
        return self.client

    def can_connect(self):
        ret = False

        client = self._get_client()

        response = client.healthChecks().list(project=self.project).execute()

        return len(response) > 0

    #######################################################
    # Cloud infra functions                               #
    #######################################################

    def prepare_sandbox_infra(self, cloud_provider_resource, prepare_infra_action, create_keys_action,
                              prepare_subnet_actions, cancellation_context, reservation_id):
        """
        :param GcCloudProvider cloud_provider_resource:
        :param PrepareCloudInfra prepare_infra_action:
        :param CreateKeys create_keys_action:
        :param List[PrepareSubnet] prepare_subnet_actions:
        :param CancellationContext cancellation_context:
        :return:
        :rtype:
        """

        results = []
        client = self._get_client()

        #check_cancellation_context_and_do_rollback(cancellation_context)

        cidr = prepare_infra_action.actionParams.cidr
        network_link = None
        region = "us-west1" #TODO: take from resource, maybe in init

        try:
            # handle PrepareInfraAction - extract sandbox CIDR and create/allocate a network in the cloud provider with
            # an address range of the provided CIDR
            self.logger.info("Received CIDR {0} from server".format(cidr))

            # network_custom = driver.ex_create_network('networkvpc1', cidr=None, mode='custom')
            # region = 'us-west1'
            # #cidr = '192.168.17.0/24'
            # subnet = driver.ex_create_subnetwork('sub1', cidr, network_custom, region)
            # #network_custom = client.ex_get_network('networkvpc1')

            #HeavenlyCloudService.prepare_infra(cloud_provider_resource, cidr)

            network_name = "netvpc-" + reservation_id

            network_body = {
                "routingConfig": {
                    "routingMode": "REGIONAL"
                },
                "name": network_name,
                "autoCreateSubnetworks": False
            }

            request = client.networks().insert(project=self.project, body=network_body)
            response = request.execute()
            global_wait(client, self.project, response['name'])

            request = client.networks().get(project=self.project, network=network_name)
            response = request.execute()
            network_link = response["selfLink"]

            results.append(PrepareCloudInfraResult(prepare_infra_action.actionId))
        except:
            self.logger.error(traceback.format_exc())
            results.append(PrepareCloudInfraResult(prepare_infra_action.actionId,
                                                   success=False,
                                                   errorMessage=traceback.format_exc()))

        #check_cancellation_context_and_do_rollback(cancellation_context)

        try:
            # handle CreateKeys - generate key pair or get it from the cloud provider and save it in a secure location
            # that will be accessible from the Deploy method
            # sandbx_ssh_key = HeavenlyCloudService.get_or_create_ssh_key()
            sandbx_ssh_key = "abcd" #TODO: implement
            results.append(CreateKeysActionResult(create_keys_action.actionId, accessKey=sandbx_ssh_key))
        except:
            self.logger.error(traceback.format_exc())
            results.append(CreateKeysActionResult(create_keys_action.actionId,
                                                  success=False,
                                                  errorMessage=traceback.format_exc()))

        #check_cancellation_context_and_do_rollback(cancellation_context)

        # handle PrepareSubnetsAction
        for action in prepare_subnet_actions:
            try:
                # subnet = driver.ex_create_subnetwork('sub1', action.actionParams.cidr, network_custom, region)
                #network_custom = client.ex_get_network('networkvpc1')

                subnet_name = self.normalize_name(action.actionParams.alias) + '-' + str(uuid.uuid4())[:6]
                cidr = action.actionParams.cidr
                subnetwork_body = {
                    "privateIpGoogleAccess": False,
                    "enableFlowLogs": False,
                    "name": subnet_name,
                    "ipCidrRange": cidr,
                    "network": network_link
                }

                request = client.subnetworks().insert(project=self.project, region=region, body=subnetwork_body)
                response = request.execute()
                region_wait(client, self.project, region, response['name'])

                # subnet_id = HeavenlyCloudService.prepare_subnet(action.actionParams.cidr,
                #                                                 action.actionParams.isPublic,
                #                                                 action.actionParams.subnetServiceAttributes)
                results.append(PrepareSubnetActionResult(action.actionId, subnet_id=subnet_name))
            except:
                self.logger.error(traceback.format_exc())
                results.append(PrepareSubnetActionResult(action.actionId,
                                                         success=False,
                                                         errorMessage=traceback.format_exc()))

        #check_cancellation_context_and_do_rollback(cancellation_context)

        return results

    def cleanup_sandbox_infra(self, cloud_provider_resource, cleanup_action, reservation_id):
        # this is the place were we remove all sandbox infra resources from the cloud provider like network, storage,
        # ssh keys, etc
        client = self._get_client()

        network_name = "netvpc-" + reservation_id
        region = "us-west1"  # TODO: take from resource, maybe in init

        request = client.networks().get(project=self.project, network=network_name)
        response = request.execute()

        for sn in response['subnetworks']:
            request = client.subnetworks().delete(project=self.project, region=region, subnetwork=sn.split("/")[-1])
            response = request.execute()
            region_wait(client, self.project, region, response['name'])

        request = client.networks().delete(project=self.project, network=network_name)
        response = request.execute()
        #global_wait(client, self.project, response['name']) # no need to wait at teardown

        return CleanupNetworkResult(actionId=cleanup_action.actionId)

    #######################################################
    # VM functions                                        #
    #######################################################

    def deploy_instance(self, context, cloudshell_session, cloud_provider_resource, deploy_app_action, connect_subnet_actions,
                     cancellation_context):

        try:
            #check_cancellation_context(cancellation_context)

            #deployment_model = deploy_app_action.actionParams.deployment.customModel

            # generate unique name to avoid name collisions
            #allowed name pattern: (?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?)
            #TODO: replace characters not matching the allowed pattern
            vm_unique_name = self.normalize_name(deploy_app_action.actionParams.appName) + '--' + str(uuid.uuid4())[:6]

            # input_user = deploy_app_action.actionParams.appResource.attributes['User']
            # encrypted_pass = deploy_app_action.actionParams.appResource.attributes['Password']
            # decrypted_input_password = cloudshell_session.DecryptPassword(encrypted_pass).Value

            deployed_app_attributes = []

            # if not decrypted_input_password:
            #     decrypted_input_password = HeavenlyCloudService.create_new_password(cloud_provider_resource, input_user,
            #                                                                         decrypted_input_password)
            #     # optional
            #     # deployedAppAttributes contains the attributes on the deployed app
            #     # use to override attributes default values
            #     deployed_app_attributes.append(Attribute('Password', decrypted_input_password))

            # convert the ConnectSubnet actions to networking metadata for cloud provider SDK
            network_data = self.prepare_network_for_instance(connect_subnet_actions)

            deployment_model_attributes = deploy_app_action.actionParams.deployment.attributes
            deployment_path = deploy_app_action.actionParams.deployment.deploymentPath
            try:
                # using cloud provider SDK, creating the instance
                # TODO: take the attributes from somewhere else (or get them as inputs to this function)
                deploy_result = self._create_instance(deploy_app_action.actionId,
                                                      cloud_provider_resource,
                                                      vm_unique_name,
                                                      deployment_model_attributes[deployment_path + '.Image Project'],
                                                      deployment_model_attributes[deployment_path + '.Image Id'],
                                                      deployment_model_attributes[deployment_path + '.Machine Type'],
                                                      deployment_model_attributes[deployment_path + '.Disk Type'],
                                                      deployment_model_attributes[deployment_path + '.Disk Size'],
                                                      network_data,
                                                      image_source_type=deployment_model_attributes[deployment_path + '.Image Source'])
            except Exception as e:
                self.logger.exception("==>")
                return DeployAppResult(actionId=deploy_app_action.actionId, success=False, errorMessage=e.message)

            connect_subnet_results = []
            for connect_subnet_action in connect_subnet_actions:
                connect_subnet_results.append(
                    ConnectToSubnetActionResult(connect_subnet_action.actionId,
                                                interface=network_data[connect_subnet_action.actionParams.subnetId]))

            #check_cancellation_context_and_do_rollback(cancellation_context)
            result = [deploy_result]
            if len(connect_subnet_results) > 0:
                result.extend(connect_subnet_results)

            return result
        except Exception as ex:
            self.logger.error(ex.message)
            raise ex

    def deploy_instance_from_template(self, context, cloudshell_session, cloud_provider_resource, deploy_app_action,
                                          connect_subnet_actions,
                                          cancellation_context):
        try:
            # generate unique name to avoid name collisions
            #allowed name pattern: (?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?)
            #TODO: replace characters not matching the allowed pattern
            vm_unique_name = self.normalize_name(deploy_app_action.actionParams.appName) + '--' + str(uuid.uuid4())[:6]

            # input_user = deploy_app_action.actionParams.appResource.attributes['User']
            # encrypted_pass = deploy_app_action.actionParams.appResource.attributes['Password']
            # decrypted_input_password = cloudshell_session.DecryptPassword(encrypted_pass).Value

            deployed_app_attributes = []

            # if not decrypted_input_password:
            #     decrypted_input_password = HeavenlyCloudService.create_new_password(cloud_provider_resource, input_user,
            #                                                                         decrypted_input_password)
            #     # optional
            #     # deployedAppAttributes contains the attributes on the deployed app
            #     # use to override attributes default values
            #     deployed_app_attributes.append(Attribute('Password', decrypted_input_password))

            # convert the ConnectSubnet actions to networking metadata for cloud provider SDK
            network_data = self.prepare_network_for_instance(connect_subnet_actions)

            deployment_model_attributes = deploy_app_action.actionParams.deployment.attributes
            deployment_path = deploy_app_action.actionParams.deployment.deploymentPath
            try:
                # using cloud provider SDK, creating the instance
                # TODO: take the attributes from somewhere else (or get them as inputs to this function)
                deploy_result = self._create_instance_from_template(deploy_app_action.actionId,
                                                                    cloud_provider_resource,
                                                                    vm_unique_name,
                                                                    deployment_model_attributes[deployment_path + '.Template Name'],
                                                                    network_data)
            except Exception as e:
                return DeployAppResult(actionId=deploy_app_action.actionId, success=False, errorMessage=e.message)

            connect_subnet_results = []
            for connect_subnet_action in connect_subnet_actions:
                connect_subnet_results.append(
                    ConnectToSubnetActionResult(connect_subnet_action.actionId,
                                                interface=network_data[connect_subnet_action.actionParams.subnetId]))

            #check_cancellation_context_and_do_rollback(cancellation_context)
            result = [deploy_result]
            if len(connect_subnet_results) > 0:
                result.extend(connect_subnet_results)

            return result
        except Exception as ex:
            self.logger.error(ex.message)
            raise ex

    def _create_instance(self, actionId, cloud_provider_resource, vm_unique_name, image_project, image_id, machine_type,
                         disk_type, disk_size, network_data, input_user='', decrypted_input_password='',
                         image_source_type='public'):

        client = self._get_client()

        region = "us-west1"  # TODO: take from resource, maybe in init
        zone = 'us-west1-b' # TODO: take from app? or cp?
        subnet = network_data.keys()[0] # TODO: handle multiple networks?
        disk_size = disk_size.lower().replace("gb","") # just in case someone provides value as 10GB

        diskType = disk_type.lower()

        source_image_uri = self._prepare_source_image(image_id, image_project, image_source_type)

        instance_body = {
            "kind": "compute#instance",
            "name": vm_unique_name,
            "zone": "projects/{}/zones/{}".format(self.project, zone),
            "machineType": "projects/{}/zones/{}/machineTypes/{}".format(self.project, zone, machine_type),
            "displayDevice": {
                "enableDisplay": False
            },
            "metadata": {
                "kind": "compute#metadata",
                "items": []
            },
            "tags": {
                "items": []
            },
            "disks": [
                {
                    "kind": "compute#attachedDisk",
                    "type": "PERSISTENT",
                    "boot": True,
                    "mode": "READ_WRITE",
                    "autoDelete": True,
                    "deviceName": "instance-1",
                    "initializeParams": {
                        "sourceImage": source_image_uri,
                        "diskType": "projects/{}/zones/{}/diskTypes/pd-{}".format(self.project, zone, diskType),
                        "diskSizeGb": disk_size
                    }
                }
            ],
            "canIpForward": False,
            "networkInterfaces": [
                {
                    "kind": "compute#networkInterface",
                    "subnetwork": "projects/{}/regions/{}/subnetworks/{}".format(self.project, region, subnet),
                    "accessConfigs": [
                        {
                            "kind": "compute#accessConfig",
                            "name": "External NAT",
                            "type": "ONE_TO_ONE_NAT",
                            "networkTier": "STANDARD"
                        }
                    ],
                    "aliasIpRanges": []
                }
            ],
            "description": "",
            "labels": {},
            "scheduling": {
                "preemptible": False,
                "onHostMaintenance": "MIGRATE",
                "automaticRestart": True,
                "nodeAffinities": []
            },
            "deletionProtection": False
        }

        self.logger.info("instance_body: " + str(instance_body))

        request = client.instances().insert(project=self.project, zone=zone, body=instance_body)
        response = request.execute()
        zone_wait(client, self.project, zone, response['name'])

        vm_details_data = self.extract_vm_details(vm_unique_name, zone)

        return DeployAppResult(actionId=actionId,
                               success=True,
                               vmUuid=vm_details_data.vmInstanceData[0].value,
                               vmName=vm_unique_name,
                               deployedAppAddress=vm_details_data.vmNetworkData[0].privateIpAddress,
                               vmDetailsData=vm_details_data)

    def _prepare_source_image(self, image_id, image_project, image_source_type):
        source_image_uri = ""
        if image_source_type == "public":
            source_image_uri = "projects/{}/global/images/{}".format(image_project, image_id)
        elif image_source_type == "private":
            source_image_uri = "global/images/{}".format(image_id)
        else:
            raise ValueError("Unsupported image source {}".format(image_source_type))

        return source_image_uri

    def _create_instance_from_template(self, actionId, cloud_provider_resource, vm_unique_name, template_name,
                                       network_data, input_user='', decrypted_input_password=''):

        client = self._get_client()

        region = "us-west1"  # TODO: take from resource, maybe in init
        zone = 'us-west1-b' # TODO: take from app? or cp?
        subnet = network_data.keys()[0] # TODO: handle multiple networks?

        request = client.instanceTemplates().get(project=self.project, instanceTemplate=template_name)
        response = request.execute()
        instance_template_url = response["selfLink"]

        body_for_template = {"name": vm_unique_name,
                             "networkInterfaces": [
                                 {
                                     "kind": "compute#networkInterface",
                                     "subnetwork": "projects/{}/regions/{}/subnetworks/{}".format(self.project, region,
                                                                                                  subnet),
                                     "accessConfigs": [
                                         {
                                             "kind": "compute#accessConfig",
                                             "name": "External NAT",
                                             "type": "ONE_TO_ONE_NAT",
                                             "networkTier": "STANDARD"
                                         }
                                     ],
                                     "aliasIpRanges": []
                                 }]}
        request = client.instances().insert(project=self.project, zone=zone, body=body_for_template,
                                            sourceInstanceTemplate=instance_template_url)
        response = request.execute()
        zone_wait(client, self.project, zone, response['name'])

        vm_details_data = self.extract_vm_details(vm_unique_name, zone)

        return DeployAppResult(actionId=actionId,
                               success=True,
                               vmUuid=vm_details_data.vmInstanceData[0].value,
                               vmName=vm_unique_name,
                               deployedAppAddress=vm_details_data.vmNetworkData[0].privateIpAddress,
                               vmDetailsData=vm_details_data)

    def delete_vm(self, instance_name):

        client = self._get_client()

        zone = 'us-west1-b'  # TODO: take from app? or cp?

        request = client.instances().delete(project=self.project, zone=zone, instance=instance_name)
        response = request.execute()
        zone_wait(client, self.project, zone, response['name'])
        return True

    def set_power_on(self, vm_uuid):
        pass

    def set_power_off(self, vm_uuid):
        pass

    def extract_vm_details(self, vm_unique_name, zone):

        client = self._get_client()
        request = client.instances().get(project=self.project, zone=zone, instance=vm_unique_name)
        response = request.execute()

        vm_instance_data = [
            VmDetailsProperty(key='Instance Id', value=response['id'])
        ]
        vm_network_data = []

        i = 0
        for nic in response['networkInterfaces']:
            network_data = [
                VmDetailsProperty(key='Name', value=nic['name']),
            ]

            public_ip = ''
            if 'accessConfigs' in nic:
                if len(nic['accessConfigs'])>0:
                    public_ip = nic['accessConfigs'][0]['natIP']

            current_interface = VmDetailsNetworkInterface(interfaceId=i,
                                                          networkId=nic['subnetwork'].split('/')[-1],
                                                          isPredefined=True,
                                                          networkData=network_data,
                                                          privateIpAddress=nic['networkIP'],
                                                          publicIpAddress=public_ip)
            i += 1
            vm_network_data.append(current_interface)

        return VmDetailsData(vmInstanceData=vm_instance_data, vmNetworkData=vm_network_data)

    def get_vm_details(self, vm_name):

        zone = 'us-west1-b'  # TODO: take from app? or cp?
        vm_details = self.extract_vm_details(vm_name, zone)
        vm_details.appName = vm_name

        return vm_details

    def refresh_ip(self, cloudshell_session, app_fullname, app_private_ip, app_public_ip, ip_regex):

        IP_V4_PATTERN = re.compile('^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')

        zone = 'us-west1-b'  # TODO: take from app? or cp?

        is_ip_match = re.compile(ip_regex).match

        vm_details = self.extract_vm_details(app_fullname, zone)
        network_data = vm_details.vmNetworkData[0]
        private_ip = network_data.privateIpAddress
        public_ip = network_data.publicIpAddress

        if private_ip:
            if IP_V4_PATTERN.match(private_ip) and is_ip_match(private_ip):
                if app_private_ip != private_ip:
                    cloudshell_session.UpdateResourceAddress(app_fullname, private_ip)

        if public_ip:
            if IP_V4_PATTERN.match(public_ip) and is_ip_match(public_ip):
                if app_public_ip != public_ip:
                    cloudshell_session.SetAttributeValue(app_fullname, "Public IP", public_ip)


    #######################################################
    # Below are not needed for the default cloud provider #
    #######################################################

    @staticmethod
    def prepare_subnet(subnet_cidr, is_public, attributes):
        return 'subnet_id_{}'.format(str(uuid.uuid4())[:8])

    @staticmethod
    def prepare_network_for_instance(connect_subnet_actions):
        """
        :param List[ConnectSubnet] connect_subnet_actions:
        :return:
        :rtype: Dict
        """
        if not connect_subnet_actions:
            # we are in single subnet mode. need to create the instance in the default subnet
            return {'default': 0}
        else:
            result = {}
            for index, action in enumerate(connect_subnet_actions):
                # Note:
                # The 'vnicName' prop is the requested vnic to be associated with the given subnet.
                # Here we might want to inspect the vnicName prop to decide how to map subnet ids to instance interfaces.
                # vnic_name = action.actionParams.vnicName
                result[action.actionParams.subnetId] = index

            return result

    @staticmethod
    def normalize_name(name):
        new_name = name.lower().replace(' ', '-').replace('_', '-').replace('.', '-').replace('--', '')
        if new_name[0].isdigit():
            new_name = 'a' + new_name
        return new_name