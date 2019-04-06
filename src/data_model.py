from cloudshell.shell.core.driver_context import ResourceCommandContext, AutoLoadDetails, AutoLoadAttribute, \
    AutoLoadResource
from collections import defaultdict


class LegacyUtils(object):
    def __init__(self):
        self._datamodel_clss_dict = self.__generate_datamodel_classes_dict()

    def migrate_autoload_details(self, autoload_details, context):
        model_name = context.resource.model
        root_name = context.resource.name
        root = self.__create_resource_from_datamodel(model_name, root_name)
        attributes = self.__create_attributes_dict(autoload_details.attributes)
        self.__attach_attributes_to_resource(attributes, '', root)
        self.__build_sub_resoruces_hierarchy(root, autoload_details.resources, attributes)
        return root

    def __create_resource_from_datamodel(self, model_name, res_name):
        return self._datamodel_clss_dict[model_name](res_name)

    def __create_attributes_dict(self, attributes_lst):
        d = defaultdict(list)
        for attribute in attributes_lst:
            d[attribute.relative_address].append(attribute)
        return d

    def __build_sub_resoruces_hierarchy(self, root, sub_resources, attributes):
        d = defaultdict(list)
        for resource in sub_resources:
            splitted = resource.relative_address.split('/')
            parent = '' if len(splitted) == 1 else resource.relative_address.rsplit('/', 1)[0]
            rank = len(splitted)
            d[rank].append((parent, resource))

        self.__set_models_hierarchy_recursively(d, 1, root, '', attributes)

    def __set_models_hierarchy_recursively(self, dict, rank, manipulated_resource, resource_relative_addr, attributes):
        if rank not in dict: # validate if key exists
            pass

        for (parent, resource) in dict[rank]:
            if parent == resource_relative_addr:
                sub_resource = self.__create_resource_from_datamodel(
                    resource.model.replace(' ', ''),
                    resource.name)
                self.__attach_attributes_to_resource(attributes, resource.relative_address, sub_resource)
                manipulated_resource.add_sub_resource(
                    self.__slice_parent_from_relative_path(parent, resource.relative_address), sub_resource)
                self.__set_models_hierarchy_recursively(
                    dict,
                    rank + 1,
                    sub_resource,
                    resource.relative_address,
                    attributes)

    def __attach_attributes_to_resource(self, attributes, curr_relative_addr, resource):
        for attribute in attributes[curr_relative_addr]:
            setattr(resource, attribute.attribute_name.lower().replace(' ', '_'), attribute.attribute_value)
        del attributes[curr_relative_addr]

    def __slice_parent_from_relative_path(self, parent, relative_addr):
        if parent is '':
            return relative_addr
        return relative_addr[len(parent) + 1:] # + 1 because we want to remove the seperator also

    def __generate_datamodel_classes_dict(self):
        return dict(self.__collect_generated_classes())

    def __collect_generated_classes(self):
        import sys, inspect
        return inspect.getmembers(sys.modules[__name__], inspect.isclass)


class GoogleCloudProvider(object):
    def __init__(self, name):
        """
        
        """
        self.attributes = {}
        self.resources = {}
        self._cloudshell_model_name = 'Google Cloud Provider'
        self._name = name

    def add_sub_resource(self, relative_path, sub_resource):
        self.resources[relative_path] = sub_resource

    @classmethod
    def create_from_context(cls, context):
        """
        Creates an instance of NXOS by given context
        :param context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :type context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :return:
        :rtype Google Cloud Provider
        """
        result = GoogleCloudProvider(name=context.resource.name)
        for attr in context.resource.attributes:
            result.attributes[attr] = context.resource.attributes[attr]
        return result

    def create_autoload_details(self, relative_path=''):
        """
        :param relative_path:
        :type relative_path: str
        :return
        """
        resources = [AutoLoadResource(model=self.resources[r].cloudshell_model_name,
            name=self.resources[r].name,
            relative_address=self._get_relative_path(r, relative_path))
            for r in self.resources]
        attributes = [AutoLoadAttribute(relative_path, a, self.attributes[a]) for a in self.attributes]
        autoload_details = AutoLoadDetails(resources, attributes)
        for r in self.resources:
            curr_path = relative_path + '/' + r if relative_path else r
            curr_auto_load_details = self.resources[r].create_autoload_details(curr_path)
            autoload_details = self._merge_autoload_details(autoload_details, curr_auto_load_details)
        return autoload_details

    def _get_relative_path(self, child_path, parent_path):
        """
        Combines relative path
        :param child_path: Path of a model within it parent model, i.e 1
        :type child_path: str
        :param parent_path: Full path of parent model, i.e 1/1. Might be empty for root model
        :type parent_path: str
        :return: Combined path
        :rtype str
        """
        return parent_path + '/' + child_path if parent_path else child_path

    @staticmethod
    def _merge_autoload_details(autoload_details1, autoload_details2):
        """
        Merges two instances of AutoLoadDetails into the first one
        :param autoload_details1:
        :type autoload_details1: AutoLoadDetails
        :param autoload_details2:
        :type autoload_details2: AutoLoadDetails
        :return:
        :rtype AutoLoadDetails
        """
        for attribute in autoload_details2.attributes:
            autoload_details1.attributes.append(attribute)
        for resource in autoload_details2.resources:
            autoload_details1.resources.append(resource)
        return autoload_details1

    @property
    def cloudshell_model_name(self):
        """
        Returns the name of the Cloudshell model
        :return:
        """
        return 'Google Cloud Provider'

    @property
    def credentials_json_path(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Credentials Json Path'] if 'Google Cloud Provider.Credentials Json Path' in self.attributes else None

    @credentials_json_path.setter
    def credentials_json_path(self, value):
        """
        Provide a path to a credentials json file or leave empty if you run from an execution server deployed on Google Cloud Compute
        :type value: str
        """
        self.attributes['Google Cloud Provider.Credentials Json Path'] = value

    @property
    def project(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.project'] if 'Google Cloud Provider.project' in self.attributes else None

    @project.setter
    def project(self, value):
        """
        
        :type value: str
        """
        self.attributes['Google Cloud Provider.project'] = value

    @property
    def networking_type(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Networking type'] if 'Google Cloud Provider.Networking type' in self.attributes else None

    @networking_type.setter
    def networking_type(self, value):
        """
        networking type that the cloud provider implements- L2 networking (VLANs) or L3 (Subnets)
        :type value: str
        """
        self.attributes['Google Cloud Provider.Networking type'] = value

    @property
    def region(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Region'] if 'Google Cloud Provider.Region' in self.attributes else None

    @region.setter
    def region(self, value=''):
        """
        The public cloud region to be used by this cloud provider.
        :type value: str
        """
        self.attributes['Google Cloud Provider.Region'] = value

    @property
    def networks_in_use(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Networks in use'] if 'Google Cloud Provider.Networks in use' in self.attributes else None

    @networks_in_use.setter
    def networks_in_use(self, value=''):
        """
        Reserved network ranges to be excluded when allocated sandbox networks (for cloud providers with L3 networking). The syntax is a comma separated CIDR list. For example "10.0.0.0/24, 10.1.0.0/26"
        :type value: str
        """
        self.attributes['Google Cloud Provider.Networks in use'] = value

    @property
    def vlan_type(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.VLAN Type'] if 'Google Cloud Provider.VLAN Type' in self.attributes else None

    @vlan_type.setter
    def vlan_type(self, value='VLAN'):
        """
        whether to use VLAN or VXLAN (for cloud providers with L2 networking)
        :type value: str
        """
        self.attributes['Google Cloud Provider.VLAN Type'] = value

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, value):
        """
        
        :type value: str
        """
        self._name = value

    @property
    def cloudshell_model_name(self):
        """
        :rtype: str
        """
        return self._cloudshell_model_name

    @cloudshell_model_name.setter
    def cloudshell_model_name(self, value):
        """
        
        :type value: str
        """
        self._cloudshell_model_name = value


class GoogleCloudCustomVM(object):
    def __init__(self, name):
        """
        Create a single VM instance from scratch
        """
        self.attributes = {}
        self.resources = {}
        self._cloudshell_model_name = 'Google Cloud Provider.Google Cloud Custom VM'
        self._name = name

    def add_sub_resource(self, relative_path, sub_resource):
        self.resources[relative_path] = sub_resource

    @classmethod
    def create_from_context(cls, context):
        """
        Creates an instance of NXOS by given context
        :param context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :type context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :return:
        :rtype Google Cloud Custom VM
        """
        result = GoogleCloudCustomVM(name=context.resource.name)
        for attr in context.resource.attributes:
            result.attributes[attr] = context.resource.attributes[attr]
        return result

    def create_autoload_details(self, relative_path=''):
        """
        :param relative_path:
        :type relative_path: str
        :return
        """
        resources = [AutoLoadResource(model=self.resources[r].cloudshell_model_name,
            name=self.resources[r].name,
            relative_address=self._get_relative_path(r, relative_path))
            for r in self.resources]
        attributes = [AutoLoadAttribute(relative_path, a, self.attributes[a]) for a in self.attributes]
        autoload_details = AutoLoadDetails(resources, attributes)
        for r in self.resources:
            curr_path = relative_path + '/' + r if relative_path else r
            curr_auto_load_details = self.resources[r].create_autoload_details(curr_path)
            autoload_details = self._merge_autoload_details(autoload_details, curr_auto_load_details)
        return autoload_details

    def _get_relative_path(self, child_path, parent_path):
        """
        Combines relative path
        :param child_path: Path of a model within it parent model, i.e 1
        :type child_path: str
        :param parent_path: Full path of parent model, i.e 1/1. Might be empty for root model
        :type parent_path: str
        :return: Combined path
        :rtype str
        """
        return parent_path + '/' + child_path if parent_path else child_path

    @staticmethod
    def _merge_autoload_details(autoload_details1, autoload_details2):
        """
        Merges two instances of AutoLoadDetails into the first one
        :param autoload_details1:
        :type autoload_details1: AutoLoadDetails
        :param autoload_details2:
        :type autoload_details2: AutoLoadDetails
        :return:
        :rtype AutoLoadDetails
        """
        for attribute in autoload_details2.attributes:
            autoload_details1.attributes.append(attribute)
        for resource in autoload_details2.resources:
            autoload_details1.resources.append(resource)
        return autoload_details1

    @property
    def cloudshell_model_name(self):
        """
        Returns the name of the Cloudshell model
        :return:
        """
        return 'Google Cloud Custom VM'

    @property
    def image_project(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Google Cloud Custom VM.Image Project'] if 'Google Cloud Provider.Google Cloud Custom VM.Image Project' in self.attributes else None

    @image_project.setter
    def image_project(self, value=''):
        """
        The project of the image to be used for deploying the app.
        :type value: str
        """
        self.attributes['Google Cloud Provider.Google Cloud Custom VM.Image Project'] = value

    @property
    def image_id(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Google Cloud Custom VM.Image Id'] if 'Google Cloud Provider.Google Cloud Custom VM.Image Id' in self.attributes else None

    @image_id.setter
    def image_id(self, value=''):
        """
        The id of the image to be used for deploying the app.
        :type value: str
        """
        self.attributes['Google Cloud Provider.Google Cloud Custom VM.Image Id'] = value

    @property
    def machine_type(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Google Cloud Custom VM.Machine Type'] if 'Google Cloud Provider.Google Cloud Custom VM.Machine Type' in self.attributes else None

    @machine_type.setter
    def machine_type(self, value='n1-standard-1'):
        """
        The size of the instance. Can be one of the pre-defined ones or a custom one.
        :type value: str
        """
        self.attributes['Google Cloud Provider.Google Cloud Custom VM.Machine Type'] = value

    @property
    def disk_type(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Google Cloud Custom VM.Disk Type'] if 'Google Cloud Provider.Google Cloud Custom VM.Disk Type' in self.attributes else None

    @disk_type.setter
    def disk_type(self, value='Standard'):
        """
        The type of the disk drive. Standard or SSD.
        :type value: str
        """
        self.attributes['Google Cloud Provider.Google Cloud Custom VM.Disk Type'] = value

    @property
    def disk_size(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Google Cloud Custom VM.Disk Size'] if 'Google Cloud Provider.Google Cloud Custom VM.Disk Size' in self.attributes else None

    @disk_size.setter
    def disk_size(self, value='10'):
        """
        The size of the disk in GB.
        :type value: str
        """
        self.attributes['Google Cloud Provider.Google Cloud Custom VM.Disk Size'] = value

    @property
    def autoload(self):
        """
        :rtype: bool
        """
        return self.attributes['Google Cloud Provider.Google Cloud Custom VM.Autoload'] if 'Google Cloud Provider.Google Cloud Custom VM.Autoload' in self.attributes else None

    @autoload.setter
    def autoload(self, value=True):
        """
        Whether to call the autoload command during Sandbox setup
        :type value: bool
        """
        self.attributes['Google Cloud Provider.Google Cloud Custom VM.Autoload'] = value

    @property
    def wait_for_ip(self):
        """
        :rtype: bool
        """
        return self.attributes['Google Cloud Provider.Google Cloud Custom VM.Wait for IP'] if 'Google Cloud Provider.Google Cloud Custom VM.Wait for IP' in self.attributes else None

    @wait_for_ip.setter
    def wait_for_ip(self, value=True):
        """
        if set to false the deployment will not wait for the VM to get an IP address
        :type value: bool
        """
        self.attributes['Google Cloud Provider.Google Cloud Custom VM.Wait for IP'] = value

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, value):
        """
        
        :type value: str
        """
        self._name = value

    @property
    def cloudshell_model_name(self):
        """
        :rtype: str
        """
        return self._cloudshell_model_name

    @cloudshell_model_name.setter
    def cloudshell_model_name(self, value):
        """
        
        :type value: str
        """
        self._cloudshell_model_name = value


class GoogleCloudVMfromTemplate(object):
    def __init__(self, name):
        """
        Create a single VM instance from an existing template
        """
        self.attributes = {}
        self.resources = {}
        self._cloudshell_model_name = 'Google Cloud Provider.Google Cloud VM from Template'
        self._name = name

    def add_sub_resource(self, relative_path, sub_resource):
        self.resources[relative_path] = sub_resource

    @classmethod
    def create_from_context(cls, context):
        """
        Creates an instance of NXOS by given context
        :param context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :type context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :return:
        :rtype Google Cloud VM from Template
        """
        result = GoogleCloudVMfromTemplate(name=context.resource.name)
        for attr in context.resource.attributes:
            result.attributes[attr] = context.resource.attributes[attr]
        return result

    def create_autoload_details(self, relative_path=''):
        """
        :param relative_path:
        :type relative_path: str
        :return
        """
        resources = [AutoLoadResource(model=self.resources[r].cloudshell_model_name,
            name=self.resources[r].name,
            relative_address=self._get_relative_path(r, relative_path))
            for r in self.resources]
        attributes = [AutoLoadAttribute(relative_path, a, self.attributes[a]) for a in self.attributes]
        autoload_details = AutoLoadDetails(resources, attributes)
        for r in self.resources:
            curr_path = relative_path + '/' + r if relative_path else r
            curr_auto_load_details = self.resources[r].create_autoload_details(curr_path)
            autoload_details = self._merge_autoload_details(autoload_details, curr_auto_load_details)
        return autoload_details

    def _get_relative_path(self, child_path, parent_path):
        """
        Combines relative path
        :param child_path: Path of a model within it parent model, i.e 1
        :type child_path: str
        :param parent_path: Full path of parent model, i.e 1/1. Might be empty for root model
        :type parent_path: str
        :return: Combined path
        :rtype str
        """
        return parent_path + '/' + child_path if parent_path else child_path

    @staticmethod
    def _merge_autoload_details(autoload_details1, autoload_details2):
        """
        Merges two instances of AutoLoadDetails into the first one
        :param autoload_details1:
        :type autoload_details1: AutoLoadDetails
        :param autoload_details2:
        :type autoload_details2: AutoLoadDetails
        :return:
        :rtype AutoLoadDetails
        """
        for attribute in autoload_details2.attributes:
            autoload_details1.attributes.append(attribute)
        for resource in autoload_details2.resources:
            autoload_details1.resources.append(resource)
        return autoload_details1

    @property
    def cloudshell_model_name(self):
        """
        Returns the name of the Cloudshell model
        :return:
        """
        return 'Google Cloud VM from Template'

    @property
    def template_name(self):
        """
        :rtype: str
        """
        return self.attributes['Google Cloud Provider.Google Cloud VM from Template.Template Name'] if 'Google Cloud Provider.Google Cloud VM from Template.Template Name' in self.attributes else None

    @template_name.setter
    def template_name(self, value=''):
        """
        The name of the template that should be used
        :type value: str
        """
        self.attributes['Google Cloud Provider.Google Cloud VM from Template.Template Name'] = value

    @property
    def autoload(self):
        """
        :rtype: bool
        """
        return self.attributes['Google Cloud Provider.Google Cloud VM from Template.Autoload'] if 'Google Cloud Provider.Google Cloud VM from Template.Autoload' in self.attributes else None

    @autoload.setter
    def autoload(self, value=True):
        """
        Whether to call the autoload command during Sandbox setup
        :type value: bool
        """
        self.attributes['Google Cloud Provider.Google Cloud VM from Template.Autoload'] = value

    @property
    def wait_for_ip(self):
        """
        :rtype: bool
        """
        return self.attributes['Google Cloud Provider.Google Cloud VM from Template.Wait for IP'] if 'Google Cloud Provider.Google Cloud VM from Template.Wait for IP' in self.attributes else None

    @wait_for_ip.setter
    def wait_for_ip(self, value=True):
        """
        if set to false the deployment will not wait for the VM to get an IP address
        :type value: bool
        """
        self.attributes['Google Cloud Provider.Google Cloud VM from Template.Wait for IP'] = value

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, value):
        """
        
        :type value: str
        """
        self._name = value

    @property
    def cloudshell_model_name(self):
        """
        :rtype: str
        """
        return self._cloudshell_model_name

    @cloudshell_model_name.setter
    def cloudshell_model_name(self, value):
        """
        
        :type value: str
        """
        self._cloudshell_model_name = value



