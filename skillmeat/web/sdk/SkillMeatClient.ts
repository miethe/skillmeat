/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BaseHttpRequest } from './core/BaseHttpRequest';
import type { OpenAPIConfig } from './core/OpenAPI';
import { FetchHttpRequest } from './core/FetchHttpRequest';
import { AnalyticsService } from './services/AnalyticsService';
import { ArtifactsService } from './services/ArtifactsService';
import { BundlesService } from './services/BundlesService';
import { CacheService } from './services/CacheService';
import { CollectionsService } from './services/CollectionsService';
import { ContextEntitiesService } from './services/ContextEntitiesService';
import { ContextSyncService } from './services/ContextSyncService';
import { DeploymentsService } from './services/DeploymentsService';
import { DiscoveryService } from './services/DiscoveryService';
import { GroupsService } from './services/GroupsService';
import { HealthService } from './services/HealthService';
import { MarketplaceService } from './services/MarketplaceService';
import { MarketplaceSourcesService } from './services/MarketplaceSourcesService';
import { MatchService } from './services/MatchService';
import { McpService } from './services/McpService';
import { MergeService } from './services/MergeService';
import { MetricsService } from './services/MetricsService';
import { ProjectsService } from './services/ProjectsService';
import { ProjectTemplatesService } from './services/ProjectTemplatesService';
import { RatingsService } from './services/RatingsService';
import { RootService } from './services/RootService';
import { SettingsService } from './services/SettingsService';
import { TagsService } from './services/TagsService';
import { UserCollectionsService } from './services/UserCollectionsService';
import { VersionsService } from './services/VersionsService';
type HttpRequestConstructor = new (config: OpenAPIConfig) => BaseHttpRequest;
export class SkillMeatClient {
  public readonly analytics: AnalyticsService;
  public readonly artifacts: ArtifactsService;
  public readonly bundles: BundlesService;
  public readonly cache: CacheService;
  public readonly collections: CollectionsService;
  public readonly contextEntities: ContextEntitiesService;
  public readonly contextSync: ContextSyncService;
  public readonly deployments: DeploymentsService;
  public readonly discovery: DiscoveryService;
  public readonly groups: GroupsService;
  public readonly health: HealthService;
  public readonly marketplace: MarketplaceService;
  public readonly marketplaceSources: MarketplaceSourcesService;
  public readonly match: MatchService;
  public readonly mcp: McpService;
  public readonly merge: MergeService;
  public readonly metrics: MetricsService;
  public readonly projects: ProjectsService;
  public readonly projectTemplates: ProjectTemplatesService;
  public readonly ratings: RatingsService;
  public readonly root: RootService;
  public readonly settings: SettingsService;
  public readonly tags: TagsService;
  public readonly userCollections: UserCollectionsService;
  public readonly versions: VersionsService;
  public readonly request: BaseHttpRequest;
  constructor(
    config?: Partial<OpenAPIConfig>,
    HttpRequest: HttpRequestConstructor = FetchHttpRequest
  ) {
    this.request = new HttpRequest({
      BASE: config?.BASE ?? 'http://localhost:8080',
      VERSION: config?.VERSION ?? '0.1.0-alpha',
      WITH_CREDENTIALS: config?.WITH_CREDENTIALS ?? false,
      CREDENTIALS: config?.CREDENTIALS ?? 'include',
      TOKEN: config?.TOKEN,
      USERNAME: config?.USERNAME,
      PASSWORD: config?.PASSWORD,
      HEADERS: config?.HEADERS,
      ENCODE_PATH: config?.ENCODE_PATH,
    });
    this.analytics = new AnalyticsService(this.request);
    this.artifacts = new ArtifactsService(this.request);
    this.bundles = new BundlesService(this.request);
    this.cache = new CacheService(this.request);
    this.collections = new CollectionsService(this.request);
    this.contextEntities = new ContextEntitiesService(this.request);
    this.contextSync = new ContextSyncService(this.request);
    this.deployments = new DeploymentsService(this.request);
    this.discovery = new DiscoveryService(this.request);
    this.groups = new GroupsService(this.request);
    this.health = new HealthService(this.request);
    this.marketplace = new MarketplaceService(this.request);
    this.marketplaceSources = new MarketplaceSourcesService(this.request);
    this.match = new MatchService(this.request);
    this.mcp = new McpService(this.request);
    this.merge = new MergeService(this.request);
    this.metrics = new MetricsService(this.request);
    this.projects = new ProjectsService(this.request);
    this.projectTemplates = new ProjectTemplatesService(this.request);
    this.ratings = new RatingsService(this.request);
    this.root = new RootService(this.request);
    this.settings = new SettingsService(this.request);
    this.tags = new TagsService(this.request);
    this.userCollections = new UserCollectionsService(this.request);
    this.versions = new VersionsService(this.request);
  }
}
