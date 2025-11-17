/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BaseHttpRequest } from './core/BaseHttpRequest';
import type { OpenAPIConfig } from './core/OpenAPI';
import { FetchHttpRequest } from './core/FetchHttpRequest';
import { HealthService } from './services/HealthService';
import { RootService } from './services/RootService';
type HttpRequestConstructor = new (config: OpenAPIConfig) => BaseHttpRequest;
export class SkillMeatClient {
    public readonly health: HealthService;
    public readonly root: RootService;
    public readonly request: BaseHttpRequest;
    constructor(config?: Partial<OpenAPIConfig>, HttpRequest: HttpRequestConstructor = FetchHttpRequest) {
        this.request = new HttpRequest({
            BASE: config?.BASE ?? (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL
                ? process.env.NEXT_PUBLIC_API_URL
                : 'http://localhost:8080'),
            VERSION: config?.VERSION ?? '0.1.0-alpha',
            WITH_CREDENTIALS: config?.WITH_CREDENTIALS ?? false,
            CREDENTIALS: config?.CREDENTIALS ?? 'include',
            TOKEN: config?.TOKEN,
            USERNAME: config?.USERNAME,
            PASSWORD: config?.PASSWORD,
            HEADERS: config?.HEADERS,
            ENCODE_PATH: config?.ENCODE_PATH,
        });
        this.health = new HealthService(this.request);
        this.root = new RootService(this.request);
    }
}

