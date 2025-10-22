import json
import boto3
import datetime

# Initialize Boto3 clients
ec2_client = boto3.client('ec2')
cloudwatch_client = boto3.client('cloudwatch')

def get_ec2_cpu_utilization(instance_id: str) -> dict:
    """
    Retrieves the average CPU utilization for an EC2 instance over the last 24 hours 
    and the instance's current type.

    :param instance_id: The ID of the EC2 instance (e.g., i-0abcdef1234567890).
    :return: A dictionary containing the instance type and the average CPU utilization.
    """
    try:
        # 1. Get Instance Type (EC2)
        ec2_response = ec2_client.describe_instances(
            InstanceIds=[instance_id]
        )

        # Navigate to the instance type
        instance_type = ec2_response['Reservations'][0]['Instances'][0]['InstanceType']

        # 2. Get CPU Utilization (CloudWatch)
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=24)

        cloudwatch_response = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600, # 1-hour periods
            Statistics=['Average']
        )

        cpu_average = 0.0
        data_points = cloudwatch_response.get('Datapoints', [])

        if data_points:
            # Calculate the average of all data points
            total_cpu = sum(p['Average'] for p in data_points)
            cpu_average = total_cpu / len(data_points)

        # 3. Return the consolidated results
        return {
            "instance_id": instance_id,
            "instance_type": instance_type,
            "average_cpu_utilization_24h": round(cpu_average, 2),
            "message": f"Successfully retrieved data for {instance_id}. Average CPU: {round(cpu_average, 2)}%. Current Type: {instance_type}"
        }

    except Exception as e:
        print(f"Error retrieving data for {instance_id}: {e}")
        return {
            "instance_id": instance_id,
            "error": str(e),
            "message": f"Failed to retrieve data for {instance_id}. Check instance ID or permissions."
        }

# The main handler for the Lambda
def lambda_handler(event, context):
    # Bedrock Agent sends the action group name and the body of the request
    action = event['actionGroup']
    api_path = event['apiPath']

    # We only expect calls to our defined function
    if api_path == '/get_ec2_cpu_utilization':
        parameters = json.loads(event['requestBody']['content']['application/json']['body'])
        instance_id = parameters.get('instance_id')

        result = get_ec2_cpu_utilization(instance_id)

        # Format the response for the Bedrock Agent
        response_body = {'application/json': {'body': json.dumps(result)}}

        return {
            'response': {
                'actionGroup': action,
                'apiPath': api_path,
                'httpMethod': event['httpMethod'],
                'httpStatusCode': 200,
                'responseBody': response_body
            }
        }

    # Handle unexpected paths/methods
    raise Exception(f"Unsupported API path: {api_path}")