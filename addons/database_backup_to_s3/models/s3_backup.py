import datetime
import logging
import os.path
import sys

try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib
import socket
import requests
import os
import shutil
import functools
import time
import base64
import glob
import odoo
import re
from odoo import models, fields, api, tools, _
import pip

try:
    from botocore.client import Config
except ImportError:
    print('\n There was no such module named -botocore- installed')
    print('xxxxxxxxxxxxxxxx installing botocore xxxxxxxxxxxxxx')
    pip.main(['install', 'botocore'])

try:
    from boto3.session import Session
except ImportError:
    print('\n There was no such module named -boto- installed')
    print('xxxxxxxxxxxxxxxx installing boto xxxxxxxxxxxxxx')
    pip.main(['install', 'boto3'])

_logger = logging.getLogger(__name__)


def execute(connector, method, *args):
    res = False
    try:
        res = getattr(connector, method)(*args)
    except socket.error as e:
        raise e
    return res


addons_path = tools.config['addons_path'] + '/auto_backup/DBbackups'


class Configuration(models.Model):
    _name = 's3.configure'
    _description = 'Configuración de S3 Backups'

    auth_key = fields.Char(
        String='User Authentication Key', required=True, store=True)
    auth_secret = fields.Char(
        String='User Authentication Secret', required=True, store=True)
    bucket_name = fields.Char(String='S3 Bucket Name',
                              required=True, store=True)
    source = fields.Char(String="Source Location",
                         help="this will be the location where the auto backup has saved the file in your local drive",
                         required=True, store=True)
    destination = fields.Char(String="Destination Location",
                              default="/", help="this will the s3 bucket source location", store=True)
    location = fields.Selection([('us-east-2', 'US East (Ohio)'), ('us-east-1', 'US East (N. Virginia)'),
                                 ('us-west-1', 'US West (N. California)'), ('us-west-2', 'US West (Oregon)'),
                                 ('ap-south-1', 'Asia Pacific (Mumbai)'),
                                 ('ap-northeast-2', 'Asia Pacific (Seoul)'),
                                 ('ap-southeast-1', 'Asia Pacific (Singapore)'),
                                 ('ap-southeast-2', 'Asia Pacific (Sydney)'),
                                 ('ap-northeast-1', 'Asia Pacific (Tokyo)'),
                                 ('ca-central-1', 'Canada (Central)'), ('eu-central-1', 'EU (Frankfurt)'),
                                 ('eu-west-1', 'EU (Ireland)'), ('eu-west-2 ', 'EU (London)'),
                                 ('sa-east-1', 'South America (Sao Paulo)'), ], string="Location")

    # @api.multi
    def get_db_list(self, host, port, context={}):
        uri = 'http://' + host + ':' + port
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
        db_list = execute(conn, 'list')
        return db_list

    # @api.multi
    def _get_db_name(self):
        dbName = self._cr.dbname
        return dbName

    # Columns for local server configuration
    host = fields.Char('Host', size=100, required=True, default='localhost')
    port = fields.Char('Port', size=10, required=True, default=8069)
    name = fields.Char('Database', size=100, required=True,
                       help='Database you want to schedule backups for', default=_get_db_name)
    backup_type = fields.Selection(
        [('zip', 'Zip'), ('dump', 'Dump')], 'Backup Type', required=True, default='zip')

    # @api.multi
    def _check_db_exist(self):
        self.ensure_one()

        db_list = self.get_db_list(self.host, self.port)
        if self.name in db_list:
            return True
        return False

    _constraints = [
        (_check_db_exist, _('Error ! No such database exists!'), [])]

    # @api.multi
    def scheduling(self):
        if not self:
            var = self.env['s3.configure'].search([('id', '=', 1)])
            var.schedule_s3_backup()
        else:
            self.schedule_s3_backup()

    # @api.multi
    def schedule_s3_backup(self):

        conf_ids = self.search([])

        for rec in conf_ids:
            db_list = self.get_db_list(rec.host, rec.port)

            if rec.name in db_list:
                try:
                    if not os.path.isdir(rec.source):
                        os.makedirs(rec.source, 0o777)
                except:
                    raise
                # Create name for dumpfile.
                bkp_file = '%s_%s.%s' % (rec.name, time.strftime('%Y-%m-%d_%H-%M-%S'), rec.backup_type)
                file_path = os.path.join(rec.source, bkp_file)
                uri = 'http://' + rec.host + ':' + rec.port
                try:
                    with open(file_path, 'wb') as fp:
                        backup = odoo.service.db.dump_db(rec.name, fp, rec.backup_type)
                        fp.close()
                        self.submit_values(file_path)
                except Exception as error:
                    _logger.debug(
                        "Couldn't backup database %s. Bad database administrator password for server running at http://%s:%s" % (
                            rec.name, rec.host, rec.port))
                    _logger.debug("Exact error from the exception: " + str(error))
                    continue
            else:
                _logger.debug("database %s doesn't exist on http://%s:%s" %
                              (rec.name, rec.host, rec.port))

    # @api.multi
    def submit_values(self, file_path):
        
        # Fill these in - you get them when you sign up for S3
        AWS_ACCESS_KEY_ID = self.auth_key
        AWS_ACCESS_KEY_SECRET = self.auth_secret
        os.environ['S3_USE_SIGV4'] = 'True'
        bucket_name = self.bucket_name
        # source directory
        sourceDir = self.source
        # destination directory name (on s3)
        destDir = self.destination
        location = self.location

        session = Session(aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_ACCESS_KEY_SECRET,
                          region_name=location)
        _s3 = session.resource("s3")

        filename = file_path
        des_filename = destDir + filename.splitlines()[0].split('/')[-1]
        sourcepath = filename
        print ('Uploading %s to Amazon S3 bucket %s' % (sourcepath, bucket_name))
        try:
            _s3.meta.client.upload_file(filename, bucket_name, des_filename)
        except Exception as error:
            _logger.debug("Exact error from the exception: " + str(error))

        os.remove(filename)
