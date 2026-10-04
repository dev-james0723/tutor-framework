import { describe, expect, test } from 'vitest';
import { authorizeResource, deriveRegion, parseRegion } from './policy';
import type { HomeRegion, RegionalResource } from './types';

describe('server-authoritative home region', () => {
  test.each([undefined,null,'', 'sg', 'us', 'CN', 1, {}])('rejects missing or invalid region %j', value => expect(() => parseRegion(value)).toThrow());
  test.each(['global','cn'] as const)('uses authenticated %s identity', homeRegion => expect(deriveRegion({userId:'u',homeRegion,emailVerified:true},homeRegion)).toBe(homeRegion));
  test('blocks client-region override', () => expect(() => deriveRegion({userId:'u',homeRegion:'cn',emailVerified:true},'cn','global')).toThrow());
  test('blocks an identity from a different deployment realm', () => expect(() => deriveRegion({userId:'u',homeRegion:'cn',emailVerified:true},'global')).toThrow());
  test('requires verified identity for persisted learning', () => expect(() => deriveRegion({userId:'u',homeRegion:'global',emailVerified:false},'global')).toThrow());
  test('never invents a home region for an incomplete identity', () => expect(() => deriveRegion({userId:'u',homeRegion:undefined,emailVerified:true},'global')).toThrow());
});

describe('resource isolation', () => {
  const cn: RegionalResource = {kind:'model',homeRegion:'cn',location:'cn-beijing',endpoint:'https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',cnApproved:true};
  test('allows explicitly approved Beijing resource', () => expect(() => authorizeResource('cn',cn)).not.toThrow());
  test.each([
    {...cn,homeRegion:'global'}, {...cn,location:'ap-southeast-1'}, {...cn,cnApproved:false},
    {...cn,endpoint:'https://dashscope-intl.aliyuncs.com/compatible-mode/v1'},
    {...cn,endpoint:'https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1'},
    {...cn,endpoint:'http://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'},
  ])('rejects CN leakage or unapproved resource %j', resource => expect(() => authorizeResource('cn',resource as RegionalResource)).toThrow());
  test('global cannot use a CN model', () => expect(() => authorizeResource('global',cn)).toThrow());
  test('model hosts cannot be disguised with suffixes', () => expect(() => authorizeResource('cn',{...cn,endpoint:'https://dashscope.aliyuncs.com.attacker.invalid/v1'})).toThrow());
  test.each(['global','cn'] as HomeRegion[])('all %s resource families enforce region identity', homeRegion => {
    for(const kind of ['database','storage','theory','email'] as const) expect(() => authorizeResource(homeRegion,{...cn,kind,homeRegion:homeRegion==='cn'?'global':'cn'})).toThrow();
  });
});
