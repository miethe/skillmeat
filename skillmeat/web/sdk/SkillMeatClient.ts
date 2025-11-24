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
import { CollectionsService } from './services/CollectionsService';
import { DeploymentsService } from './services/DeploymentsService';
import { HealthService } from './services/HealthService';
import { MarketplaceService } from './services/MarketplaceService';
import { McpService } from './services/McpService';
import { ProjectsService } from './services/ProjectsService';
import { RootService } from './services/RootService';
type HttpRequestConstructor = new (config: OpenAPIConfig) => BaseHttpRequest;
export class SkillMeatClient {
    public readonly analytics: AnalyticsService;
    public readonly artifacts: ArtifactsService;
    public readonly bundles: BundlesService;
    public readonly collections: CollectionsService;
    public readonly deployments: DeploymentsService;
    public readonly health: HealthService;
    public readonly marketplace: MarketplaceService;
    public readonly mcp: McpService;
    public readonly projects: ProjectsService;
    public readonly root: RootService;
    public readonly request: BaseHttpRequest;
    constructor(config?: Partial<OpenAPIConfig>, HttpRequest: HttpRequestConstructor = FetchHttpRequest) {
        this.request = new HttpRequest({
            BASE: config?.BASE ?? '',
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
        this.collections = new CollectionsService(this.request);
        this.deployments = new DeploymentsService(this.request);
        this.health = new HealthService(this.request);
        this.marketplace = new MarketplaceService(this.request);
        this.mcp = new McpService(this.request);
        this.projects = new ProjectsService(this.request);
        this.root = new RootService(this.request);
    }
}

