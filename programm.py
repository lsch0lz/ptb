"""" 
A AWS-Lambda for ServiceTeam-HR wich searches for Instances, Snapshots and Volumes wich are not in the managedpsp List
Simply put all the valid PSP-Elements in the mangedpsp List and run it in the AWS-Console
"""
import boto3
import json
import logging
import re
import datetime

# simple logging
logger = logging.getLogger()

# connection region (eu-central-1)
ec2 = boto3.resource('ec2', region_name="eu-central-1")
s3 = boto3.resource('s3')
snsclient = boto3.client('sns')

base = ec2.instances.all()
volumes = ec2.volumes.all()
snapshots = ec2.snapshots.all()

#List of all PSP Elements that are valid
managedpsp = ["F-250007-51-03", "F-250007-51-04", "F-330843-51-03", "F-330843-51-04", "F-390243-51-03",
              "F-390243-51-04", "F-390243-51-06", "F-390262-51-04", "F-390332-06-02", "F-390332-51-04",
              "F-390332-51-06", "F-390332-52-06", "F-390332-57-01", "F-390332-57-02", "F-390332-57-03",
              "F-390332-57-04", "F-390332-57-06"]


def lambda_handler(event, context):

    #counting variables
    count_instance = 0
    count_volume = 0
    count_snapshot = 0

    missingtagginginfo = ""

    # looping through instances
    for instance in base:

        if instance.state["Name"] == "terminated":
            continue

        #checking if PSP is set
        if (not costreference_isset(instance)):
            # print("[INSTANCE] " + str(instance))
            # print("[INFO]: No CostReferenceTag!! \n")
            missingtagginginfo = missingtagginginfo + "Instance" + '\t' +str(instance.id) + "\tNo CostReferenceTag\n"
            count_instance += 1
            continue
        else:
            # Checking for right CostReferenceTag
            costreference = get_costreferencetag(instance)

            if costreference not in managedpsp:
                # print("[INSTANCE] " + str(instance))
                # print("[INFO]: The PSP: "+costreference + " of: "+str(instance)+ " is WRONG! \n")
                missingtagginginfo = missingtagginginfo + "Instance" + '\t' +str(instance.id) + "\tWrong PSP\t" + costreference +"\n"
                count_instance += 1
    print(count_instance)

    # looping through volumes

    for vol in volumes:

        iv = ec2.Volume(str(vol.id))

        #checking if PSP is set
        if (not costreference_isset_volumes(iv)):
            # print("[VOLUME] " + str(iv))
            # print("[INFO]: No CostReferenceTag!! \n")
            missingtagginginfo = missingtagginginfo + "Volume" + "\t" + str(iv.id) + "\tNo CostReferenceTag\n"
            count_volume += 1
            continue
        else:
            costreference_volume = get_costreferncetag_volume(iv)

            if costreference_volume not in managedpsp:
                # print("[VOLUME] " + str(iv))
                # print("[INFO]: The PSP: " + costreference_volume + " of: " + str(iv) + " is WRONG! \n")
                missingtagginginfo = missingtagginginfo + "Volume" + "\t" + str(iv.id) + "\tWrong PSP\t" + costreference_volume + "\n"
                count_volume += 1
    print(count_volume)

    # looping through snapshots

    for snapshot in snapshots.filter(OwnerIds=['self']):

        # checking if PSP is set
        if (not costreferencetag_isset_snapshot(snapshot)):
            # print("[SNAPSHOT] " + str(snapshot))
            # print("[INFO]: No CostReferenceTag!! \n")
            missingtagginginfo = missingtagginginfo + "Snapshot" + "\t" + str(snapshot.id) + "\tNo CostReferenceTag\n"
            count_snapshot += 1
            continue
        else:
            costreference_snapshot = get_costreference_snapshot(snapshot)

            if costreference_snapshot not in managedpsp:
                # print("[SNAPSHOT] " + str(snapshot))
                # print("[INFO]: The PSP: " + costreference_snapshot + " of: " + str(snapshot) + " is WRONG! \n")
                missingtagginginfo = missingtagginginfo + "Snapshot" + "\t" + str(snapshot.id) + "\tWrong PSP\t" + costreference_snapshot + "\n"
                count_snapshot += 1
    print(count_snapshot)


    #Setting up s3 Bucket upload
    now = datetime.datetime.now()
    textfile = 'Summary from: ' + str(now) + '.txt'

    s3.Object('costreferencesearch', textfile).put(Body=missingtagginginfo)

    # Setting up SNS Message
    if not missingtagginginfo == "":
        print("[INFO] No Tagging for the following ressources:")
        print("[INFO] " + str(missingtagginginfo))

        print("[INFO] Sending SNS Notification to " + 'LINK ZUM SNS SERVER')
        snsresponse = snsclient.publish(TopicArn='LINK ZUM SNS SERVER', Message=str('Added new summary/ \n' + 'Instances: ' + str(count_instance) + '\n' + 'Volumes: ' + str(count_volume) + '\n' + 'Snapshots: ' + str(count_snapshot)), Subject='CostReferenceSearch: Summary.', MessageAttributes={'TaggingInfo': {'DataType': 'String', 'StringValue': 'UTF8'}})
        print("[INFO] Response: " + str(snsresponse))


### FUNCTIONS ####

def costreference_isset(instance):
    # Searching for Instance without CostReference-tags
    if instance.tags is None:
        # print("[INFO]: No Tags have been set yet:")
        return (False)

    # Searching for CostReference-tags
    for t in instance.tags:
        if t['Key'] == 'CostReference':
            return (True)
    return (False)


def get_costreferencetag(instance):
    #getting the used Costreference tag
    for t in instance.tags:
        if t['Key'] == "CostReference":
            return (str(t['Value']))

    return (False)


def costreference_isset_volumes(iv):
    if iv.tags is None:
        # print("[INFO]: No Tags have been set yet:")
        return (False)

    for t in iv.tags:
        if t['Key'] == 'CostReference':
            return (True)
    return (False)


def get_costreferncetag_volume(iv):
    for t in iv.tags:
        if t['Key'] == "CostReference":
            return (str(t['Value']))

    return (False)


def costreferencetag_isset_snapshot(snapshot):
    if snapshot.tags is None:
        # print("[INFO]: No Tags have been set yet:")
        return (False)

    # Searching for CostReference-tags
    for t in snapshot.tags:
        if t['Key'] == 'CostReference':
            return (True)
    return (False)


def get_costreference_snapshot(snapshot):
    for t in snapshot.tags:
        if t['Key'] == "CostReference":
            return (str(t['Value']))

    return (False)
