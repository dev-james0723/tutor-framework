import type { HomeRegion, ServerIdentity, RegionalResource } from './types';

export class RegionalPolicyError extends Error {
  constructor(public readonly code: 'missing_region' | 'identity_required' | 'region_boundary_blocked' | 'resource_unapproved') { super(code); this.name='RegionalPolicyError'; }
}

export function parseRegion(value: unknown): HomeRegion {
  if(value !== 'global' && value !== 'cn') throw new RegionalPolicyError('missing_region');
  return value;
}

export function deriveRegion(identity: ServerIdentity, deployed: unknown, claimed?: unknown): HomeRegion {
  if(!identity.userId || !identity.emailVerified) throw new RegionalPolicyError('identity_required');
  const region = parseRegion(identity.homeRegion);
  if(region !== parseRegion(deployed) || (claimed !== undefined && claimed !== region)) throw new RegionalPolicyError('region_boundary_blocked');
  return region;
}

export function authorizeResource(region: HomeRegion, resource: RegionalResource): void {
  const location = region === 'cn' ? 'cn-beijing' : 'ap-southeast-1';
  if(resource.homeRegion !== region || resource.location !== location || (region === 'cn' && !resource.cnApproved)) throw new RegionalPolicyError('resource_unapproved');
  let url: URL;
  try { url = new URL(resource.endpoint); } catch { throw new RegionalPolicyError('resource_unapproved'); }
  if(resource.kind === 'database') {
    if(!['postgres:','postgresql:'].includes(url.protocol)) throw new RegionalPolicyError('resource_unapproved');
    return;
  }
  if(url.protocol !== 'https:' || url.username || url.password || url.port || url.hash) throw new RegionalPolicyError('resource_unapproved');
  if(resource.kind === 'model') {
    const host = url.hostname;
    const approvedHost = region === 'cn'
      ? host === 'dashscope.aliyuncs.com' || /^[a-z0-9-]+\.cn-beijing\.maas\.aliyuncs\.com$/.test(host)
      : host === 'dashscope-intl.aliyuncs.com' || /^[a-z0-9-]+\.ap-southeast-1\.maas\.aliyuncs\.com$/.test(host);
    if(!approvedHost || url.pathname !== '/compatible-mode/v1' || url.search) throw new RegionalPolicyError('resource_unapproved');
  }
}
