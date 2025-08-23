/**
 * Connector logo registry
 * Maps connector sources to their logo assets
 */

import airtableLogo from './airtable.svg';
import asanaLogo from './asana.svg';
import azureBlobLogo from './azure-blob.svg';
import clickupLogo from './clickup.svg';
import confluenceLogo from './confluence.svg';
import csvLogo from './csv.svg';
import defaultLogo from './default.svg';
// Destination logos
import cleverBragLogo from './destinations/cleverbrag.svg';
import csvDumpLogo from './destinations/csv-dump.svg';
import onyxLogo from './destinations/onyx.svg';
import discordLogo from './discord.svg';
import dropboxLogo from './dropbox.svg';
import elasticsearchLogo from './elasticsearch.svg';
import gcsLogo from './gcs.svg';
import githubLogo from './github.svg';
// Import logos (these would be actual logo files)
import gmailLogo from './gmail.svg';
import googleDriveLogo from './google-drive.svg';
import hubspotLogo from './hubspot.svg';
import intercomLogo from './intercom.svg';
import jiraLogo from './jira.svg';
import jsonLogo from './json.svg';
import linearLogo from './linear.svg';
import mondayLogo from './monday.svg';
import mongodbLogo from './mongodb.svg';
import mysqlLogo from './mysql.svg';
import notionLogo from './notion.svg';
import oneDriveLogo from './onedrive.svg';
import postgresLogo from './postgres.svg';
import redisLogo from './redis.svg';
import rssLogo from './rss.svg';
import s3Logo from './s3.svg';
import salesforceLogo from './salesforce.svg';
import slackLogo from './slack.svg';
import teamsLogo from './teams.svg';
import webLogo from './web.svg';
import xmlLogo from './xml.svg';
import zendeskLogo from './zendesk.svg';

export const connectorLogos: Record<string, string> = {
  // Email & Communication
  gmail: gmailLogo,
  slack: slackLogo,
  discord: discordLogo,
  teams: teamsLogo,
  intercom: intercomLogo,
  zendesk: zendeskLogo,

  // Cloud Storage
  google_drive: googleDriveLogo,
  dropbox: dropboxLogo,
  onedrive: oneDriveLogo,
  s3: s3Logo,
  gcs: gcsLogo,
  azure_blob: azureBlobLogo,

  // Project Management
  notion: notionLogo,
  confluence: confluenceLogo,
  jira: jiraLogo,
  linear: linearLogo,
  asana: asanaLogo,
  monday: mondayLogo,
  clickup: clickupLogo,
  airtable: airtableLogo,

  // Development
  github: githubLogo,

  // CRM & Sales
  salesforce: salesforceLogo,
  hubspot: hubspotLogo,

  // Databases
  postgres: postgresLogo,
  mysql: mysqlLogo,
  mongodb: mongodbLogo,
  redis: redisLogo,
  elasticsearch: elasticsearchLogo,

  // Web & Feeds
  web: webLogo,
  rss: rssLogo,

  // File Formats
  csv: csvLogo,
  json: jsonLogo,
  xml: xmlLogo,

  // Default fallback
  default: defaultLogo,
};

export const destinationLogos: Record<string, string> = {
  cleverbrag: cleverBragLogo,
  onyx: onyxLogo,
  csv: csvDumpLogo,
  csvdump: csvDumpLogo,
  default: defaultLogo,
};

export const getConnectorLogo = (source: string): string => {
  return connectorLogos[source] || connectorLogos.default;
};

export const getDestinationLogo = (name: string): string => {
  return destinationLogos[name] || destinationLogos.default;
};

// Connector categories for organization
export const connectorCategories = {
  'Email & Communication': ['gmail', 'slack', 'discord', 'teams', 'intercom', 'zendesk'],
  'Cloud Storage': ['google_drive', 'dropbox', 'onedrive', 's3', 'gcs', 'azure_blob'],
  'Project Management': [
    'notion',
    'confluence',
    'jira',
    'linear',
    'asana',
    'monday',
    'clickup',
    'airtable',
  ],
  Development: ['github'],
  'CRM & Sales': ['salesforce', 'hubspot'],
  Databases: ['postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch'],
  'Web & Feeds': ['web', 'rss'],
  'File Formats': ['csv', 'json', 'xml'],
};

export const getConnectorCategory = (source: string): string => {
  for (const [category, sources] of Object.entries(connectorCategories)) {
    if (sources.includes(source)) {
      return category;
    }
  }
  return 'Other';
};
