import json
from cloudshell.cp.core import DriverRequestParser
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.cp.core.models import DriverResponse, DeployApp, PrepareCloudInfra, CreateKeys, \
    PrepareSubnet, CleanupNetwork, ConnectSubnet
from cloudshell.cp.core.utils import single
from cloudshell.shell.core.driver_context import InitCommandContext, AutoLoadCommandContext, ResourceCommandContext, \
    AutoLoadDetails, CancellationContext, ResourceRemoteCommandContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.core.context.error_handling_context import ErrorHandlingContext
from data_model import *
from ccp.gcp.gcp_service import GCPService

class GcCloudProviderDriver (ResourceDriverInterface):

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        self.request_parser = DriverRequestParser()

    def initialize(self, context):
        """
        Initialize the client session, this function is called everytime a new instance of the client is created
        This is a good place to load and cache the client configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    # <editor-fold desc="Discovery">

    @staticmethod
    def _get_service(cloud_provider_resource, logger):
        project = cloud_provider_resource.project
        json_path = cloud_provider_resource.credentials_json_path

        gcp_service = GCPService(project=project, logger=logger, json_cred_path=json_path)
        return gcp_service

    def get_inventory(self, context):
        """
        Discovers the resource structure and attributes.
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as cloudshell_session:
                self._log(logger, 'get_inventory_context_json', context)

                cloud_provider_resource = GoogleCloudProvider.create_from_context(context)

                gcp_service = self._get_service(cloud_provider_resource, logger)

                if not gcp_service.can_connect():
                    raise ValueError('Could not connect: Check credentials')

        return cloud_provider_resource.create_autoload_details()


    # </editor-fold>

    # <editor-fold desc="Mandatory Commands">

    def Deploy(self, context, request=None, cancellation_context=None):
        """
        Deploy
        :param ResourceCommandContext context:
        :param str request: A JSON string with the list of requested deployment actions
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as cloudshell_session:
                self._log(logger, 'deploy_request', request)
                self._log(logger, 'deploy_context', context)

                cloud_provider_resource = GoogleCloudProvider.create_from_context(context)

                gcp_service = self._get_service(cloud_provider_resource, logger)

                # parse the json strings into action objects
                actions = self.request_parser.convert_driver_request_to_actions(request)

                # extract DeployApp action
                deploy_action = single(actions, lambda x: isinstance(x, DeployApp))

                # extract ConnectToSubnetActions
                connect_subnet_actions = list(filter(lambda x: isinstance(x, ConnectSubnet), actions))

                # if we have multiple supported deployment options use the 'deploymentPath' property
                # to decide which deployment option to use.
                deployment_name = deploy_action.actionParams.deployment.deploymentPath

                self._log(logger, 'deployment_name', deployment_name)

                if deployment_name == 'Google Cloud Provider.Google Cloud Custom VM':
                    deploy_results = gcp_service.deploy_instance(context, cloudshell_session,
                                                                 cloud_provider_resource,
                                                                 deploy_action,
                                                                 connect_subnet_actions,
                                                                 cancellation_context)
                elif deployment_name == 'Google Cloud Provider.Google Cloud VM from Template':
                    deploy_results = gcp_service.deploy_instance_from_template(context, cloudshell_session,
                                                                               cloud_provider_resource,
                                                                               deploy_action,
                                                                               connect_subnet_actions,
                                                                               cancellation_context)
                else:
                    raise ValueError(deployment_name + ' deployment option is not supported.')

                # deploy_result = gcp_service.clone_vm(deploy_action, cloud_provider_resource.storage_container_uuid)
                #
                self._log(logger, 'deploy_result', str(deploy_results))

                return DriverResponse(deploy_results).to_driver_response_json()


    def PowerOn(self, context, ports):
        """
        Will power on the compute resource
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        pass

    def PowerOff(self, context, ports):
        """
        Will power off the compute resource
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        pass

    def PowerCycle(self, context, ports, delay):
        pass

    def DeleteInstance(self, context, ports):
        """
        Will delete the compute resource
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as cloudshell_session:
                self._log(logger, 'DeleteInstance_context', context)
                self._log(logger, 'DeleteInstance_ports', ports)
                cloud_provider_resource = GoogleCloudProvider.create_from_context(context)

                gcp_service = self._get_service(cloud_provider_resource, logger)
                resource_ep = context.remote_endpoints[0]
                gcp_service.delete_vm(resource_ep.fullname)

    def GetVmDetails(self, context, requests, cancellation_context):
        """

        :param ResourceCommandContext context:
        :param str requests:
        :param CancellationContext cancellation_context:
        :return:
        """
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as cloudshell_session:
                self._log(logger, 'GetVmDetails_context', context)
                self._log(logger, 'GetVmDetails_requests', requests)
                cloud_provider_resource = GoogleCloudProvider.create_from_context(context)

                gcp_service = self._get_service(cloud_provider_resource, logger)

                results = []

                requests_loaded = json.loads(requests)

                for request in requests_loaded[u'items']:
                    vm_name = request[u'deployedAppJson'][u'name']

                    result = gcp_service.get_vm_details(vm_name)
                    results.append(result)

                result_json = json.dumps(results, default=lambda o: o.__dict__, sort_keys=True, separators=(',', ':'))

                self._log(logger, 'GetVmDetails_result', result_json)

                return result_json

    def remote_refresh_ip(self, context, ports, cancellation_context):
        """
        Will update the address of the computer resource on the Deployed App resource in cloudshell
        :param ResourceRemoteCommandContext context:
        :param ports:
        :param CancellationContext cancellation_context:
        :return:
        """
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as cloudshell_session:
                self._log(logger, 'remote_refresh_ip_context', context)
                self._log(logger, 'remote_refresh_ip_ports', ports)
                self._log(logger, 'remote_refresh_ip_cancellation_context', cancellation_context)
                cloud_provider_resource = GoogleCloudProvider.create_from_context(context)

                gcp_service = self._get_service(cloud_provider_resource, logger)

                deployed_app_dict = json.loads(context.remote_endpoints[0].app_context.deployed_app_json)
                remote_ep = context.remote_endpoints[0]
                deployed_app_private_ip = remote_ep.address
                deployed_app_public_ip = None

                resource_attributes = self._parse_attributes(deployed_app_dict['attributes'])

                public_ip_att = self._get_custom_attribute(resource_attributes, 'Public IP', None)
                ip_regex = self._get_custom_attribute(resource_attributes, 'IP Regex', '.*')
                refresh_ip_timeout = self._get_custom_attribute(resource_attributes, 'Refresh IP Timeout', 600)

                if public_ip_att:
                    deployed_app_public_ip = public_ip_att['value']

                deployed_app_fullname = remote_ep.fullname

                gcp_service.refresh_ip(cloudshell_session, deployed_app_fullname, deployed_app_private_ip,
                                       deployed_app_public_ip, ip_regex)

    # </editor-fold>


    ### NOTE: According to the Connectivity Type of your shell, remove the commands that are not
    ###       relevant from this file and from drivermetadata.xml.

    # <editor-fold desc="Mandatory Commands For L2 Connectivity Type">

    def ApplyConnectivityChanges(self, context, request):
        """
        Configures VLANs on multiple ports or port-channels
        :param ResourceCommandContext context: The context object for the command with resource and reservation info
        :param str request: A JSON string with the list of requested connectivity changes
        :return: a json object with the list of connectivity changes which were carried out by the client
        :rtype: str
        """
        pass

    # </editor-fold> 

    # <editor-fold desc="Mandatory Commands For L3 Connectivity Type">

    def PrepareSandboxInfra(self, context, request, cancellation_context):
        """

        :param ResourceCommandContext context:
        :param str request:
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as cloudshell_session:
                self._log(logger, 'PrepareSandboxInfra_request', request)
                self._log(logger, 'PrepareSandboxInfra_context', context)

                cloud_provider_resource = GoogleCloudProvider.create_from_context(context)

                gcp_service = self._get_service(cloud_provider_resource, logger)

                # parse the json strings into action objects
                actions = self.request_parser.convert_driver_request_to_actions(request)

                # extract PrepareCloudInfra action
                prepare_infra_action = single(actions, lambda x: isinstance(x, PrepareCloudInfra))

                # extract CreateKeys action
                create_keys_action = single(actions, lambda x: isinstance(x, CreateKeys))

                # extract PrepareSubnet actions
                prepare_subnet_actions = list(filter(lambda x: isinstance(x, PrepareSubnet), actions))

                action_results = gcp_service.prepare_sandbox_infra(cloud_provider_resource,
                                                                   prepare_infra_action,
                                                                   create_keys_action,
                                                                   prepare_subnet_actions,
                                                                   cancellation_context,
                                                                   context.reservation.reservation_id)
        
                return DriverResponse(action_results).to_driver_response_json()

    def CleanupSandboxInfra(self, context, request):
        """

        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as cloudshell_session:
                self._log(logger, 'CleanupSandboxInfra_request', request)
                self._log(logger, 'CleanupSandboxInfra_context', context)

                cloud_provider_resource = GoogleCloudProvider.create_from_context(context)

                gcp_service = self._get_service(cloud_provider_resource, logger)

                # parse the json strings into action objects
                actions = self.request_parser.convert_driver_request_to_actions(request)

                # extract CleanupNetwork action
                cleanup_action = single(actions, lambda x: isinstance(x, CleanupNetwork))

                action_result = gcp_service.cleanup_sandbox_infra(cloud_provider_resource, cleanup_action,
                                                                  context.reservation.reservation_id)

                self._log(logger, 'CleanupSandboxInfra_action_result', action_result)

                return DriverResponse([action_result]).to_driver_response_json()


    # </editor-fold>

    # <editor-fold desc="Optional Commands For L3 Connectivity Type">

    def SetAppSecurityGroups(self, context, request):
        """

        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        pass

    # </editor-fold>

    def cleanup(self):
        """
        Destroy the client session, this function is called everytime a client instance is destroyed
        This is a good place to close any open sessions, finish writing to log files, etc.
        """
        pass

    def _log(self, logger, name, obj):

        if not obj:
            logger.info(name + ' Value is None')

        if not self._is_primitive(obj):
            name = name + '__json_serialized'
            obj = json.dumps(obj, default=lambda o: o.__dict__, sort_keys=True, separators=(',', ':'))

        logger.info(name)
        logger.info(obj)

    @staticmethod
    def _is_primitive(thing):
        primitive = (int, str, bool, float, unicode)
        return isinstance(thing, primitive)

    @staticmethod
    def _parse_attributes(attributes):
        result = dict()

        for each in attributes:
            result[each['name']] = each['value']

        return result

    @staticmethod
    def _get_custom_attribute(attributes, name, default):
        result = default

        if name in attributes:
            result = attributes[name]

        return result