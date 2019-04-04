import time


def zone_wait(client, project, zone, operation):
    """ input: client, project, zone, and operation
        output: request result - json
        sleep/waits for zone operation to complete
    """
    while True:
        result = client.zoneOperations().get(project=project, zone=zone, operation=operation).execute()
        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        else:
            print("waiting for " + operation)
        time.sleep(1)


def region_wait(client, project, region, operation):
    """ input: gce connection and operation
        output: request result - json
        sleep/waits for region operation to complete
    """
    while True:
        result = client.regionOperations().get(project=project, region=region, operation=operation).execute()
        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        else:
            print("waiting for " + operation)
        time.sleep(1)


def global_wait(client, project, operation):
    """ input: gce client and operation
        output: request result - json
        sleep/waits for global operation to complete
    """
    while True:
        result = client.globalOperations().get(project=project, operation=operation).execute()
        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        else:
            print("waiting for " + operation)
        time.sleep(1)
