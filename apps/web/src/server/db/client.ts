import { Pool, type PoolClient } from 'pg';
import type { HomeRegion, RegionalResource } from '../region/types';
import { authorizeResource, parseRegion, RegionalPolicyError } from '../region/policy';
import { schemaVersion } from './schema';

export async function assertDatabaseRealm(client: Pick<PoolClient,'query'>, region: HomeRegion): Promise<void> {
  const realm = await client.query('SELECT home_region FROM app_region WHERE singleton');
  if(realm.rows.length !== 1 || parseRegion(realm.rows[0].home_region) !== region) throw new RegionalPolicyError('region_boundary_blocked');
  const versions = await client.query('SELECT version FROM schema_versions ORDER BY version');
  if(versions.rows.at(-1)?.version !== schemaVersion) throw new Error('database_schema_incompatible');
}

export function createRegionalPool(region: HomeRegion, resource: RegionalResource): Pool {
  if(resource.kind !== 'database') throw new RegionalPolicyError('resource_unapproved');
  authorizeResource(region,resource);
  return new Pool({ connectionString: resource.endpoint, max: 4, connectionTimeoutMillis: 5000, idleTimeoutMillis: 30000, ssl: {rejectUnauthorized:true}, application_name: 'super-theory-tutor' });
}
