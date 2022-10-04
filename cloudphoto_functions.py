import configparser
import os
import sys

import boto3
import botocore.exceptions

import templates


def init_config():
    config = configparser.ConfigParser()
    config.read(os.path.expanduser('~/.config/cloudphotoarchive/cloudphotorc'))
    return config['DEFAULT']


bucket = init_config()['bucket']
session = boto3.session.Session()
s3_client = session.client(
    service_name='s3',
    endpoint_url=init_config()['endpoint_url'],
    aws_access_key_id=init_config()['aws_access_key_id'],
    aws_secret_access_key=init_config()['aws_secret_access_key'],
)
s3_resource = session.resource(
    service_name='s3',
    endpoint_url=init_config()['endpoint_url'],
    aws_access_key_id=init_config()['aws_access_key_id'],
    aws_secret_access_key=init_config()['aws_secret_access_key'],
)


def init():
    print('Input aws_access_key_id: ', end='')
    aws_access_key_id = input()
    print('Input aws_secret_access_key: ', end='')
    aws_secret_access_key = input()
    print('Input bucket: ', end='')
    input_bucket = input()
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'bucket': input_bucket,
        'aws_access_key_id': aws_access_key_id,
        'aws_secret_access_key': aws_secret_access_key,
        'endpoint_url': 'https://storage.yandexcloud.net',
        'region': 'ru-central1'
    }
    with open(os.path.expanduser('~/.config/cloudphotoarchive/cloudphotorc'), mode='w') as f:
        config.write(f)


def upload(album, photos_dir):
    if not os.path.exists(photos_dir):
        print(f'Directory {photos_dir} not found', file=sys.stderr)
        exit(1)
    if album is None:
        print(f'Album name not set', file=sys.stderr)
        exit(1)
    uploaded = 0
    for file in os.listdir(photos_dir):
        if not (file.endswith('.jpeg') or file.endswith('.jpg')):
            continue
        uploaded += 1
        object_name = f"{album}/{file}"
        try:
            s3_client.upload_file(os.path.join(photos_dir, file), bucket, object_name)
        except:
            print(f"Failed to upload file {file}")
    if uploaded == 0:
        print(f'Images not found', file=sys.stderr)
        exit(1)


def delete(album, photo):
    if photo is None:
        album_photos = s3_resource.Bucket(bucket).objects.filter(Prefix=album + '/')
        album_photos.delete()
    else:
        obj = s3_resource.Object(bucket, f"{album}/{photo}")
        try:
            obj.load()
            obj.delete()
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == "404":
                print(f'Photo not found', file=sys.stderr)
                exit(1)


def download(album, photos_dir):
    objects = s3_resource.Bucket(bucket).objects.filter(Prefix=album + '/')
    if len([obj for obj in objects]) == 0:
        print(f'Album {album} not exist', file=sys.stderr)
        exit(1)
    if not os.path.exists(photos_dir):
        print(f'Directory {photos_dir} not found', file=sys.stderr)
        exit(1)
    for obj in s3_resource.Bucket(bucket).objects.filter(Prefix=album + '/'):
        print(os.path.abspath(os.path.join(photos_dir, obj.key)))
        file_name = obj.key.split('/')[1]
        s3_client.download_file(bucket, obj.key, os.path.join(photos_dir, file_name))


def photo_list(album):
    if album is None:
        objects = s3_resource.Bucket(bucket).objects.all()
        objects = [obj for obj in objects]
        objects = set(
            map(lambda name: name[0], filter(lambda arr: len(arr) > 1, map(lambda o: o.key.split('/'), objects))))
        if len(objects) == 0:
            print(f'No albums', file=sys.stderr)
            exit(1)
        for obj in objects:
            print(obj)
    else:
        objects = s3_resource.Bucket(bucket).objects.filter(Prefix=album + '/')
        objects = [obj for obj in objects]
        if len(objects) == 0:
            print(f'Album {album} is empty or does not exist', file=sys.stderr)
            exit(1)
        for obj in objects:
            print(obj.key.split('/')[1])


def make_site():
    objects = s3_resource.Bucket(bucket).objects.all()
    objects = [obj for obj in objects]
    objects = set(map(lambda name: name[0], filter(lambda arr: len(arr) > 1, map(lambda o: o.key.split('/'), objects))))
    res_str = ''
    for i, a in enumerate(objects):
        res_str += templates.album_list_e.format(n=i, name=a)
    index = templates.index_template.format(album_list=res_str)
    s3_client.put_object(Bucket=bucket, Key='index.html', Body=index)
    s3_client.put_object(Bucket=bucket, Key='error.html', Body=templates.error_template)
    create_album_pages(objects, s3_client, s3_resource)
    website_configuration = {
        'ErrorDocument': {'Key': 'error.html'},
        'IndexDocument': {'Suffix': 'index.html'},
    }
    s3_client.put_bucket_website(Bucket=bucket, WebsiteConfiguration=website_configuration)
    s3_resource.BucketAcl(bucket).put(ACL='public-read')
    print(f'https://{bucket}.website.yandexcloud.net/')


def create_album_pages(albums, client, res):
    for i, album in enumerate(albums):
        photos = res.Bucket(bucket).objects.filter(Prefix=album + '/')
        photos = list(photos)
        photo_list = ''
        for photo in photos:
            photo_list += templates.photo_list_e.format(url=photo.key, name=photo.key)
        album_page = templates.album_template.format(photo_list=photo_list)
        client.put_object(Bucket=bucket, Key=f'album{i}.html', Body=album_page)
