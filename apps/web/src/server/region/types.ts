export type HomeRegion = 'global' | 'cn';
export interface ServerIdentity { userId: string; homeRegion: unknown; emailVerified: boolean }
export type RegionalLocation = 'ap-southeast-1' | 'cn-beijing';
export type ResourceKind = 'database' | 'storage' | 'theory' | 'model' | 'email';
export interface RegionalResource { kind: ResourceKind; homeRegion: HomeRegion; location: RegionalLocation; endpoint: string; cnApproved: boolean }
