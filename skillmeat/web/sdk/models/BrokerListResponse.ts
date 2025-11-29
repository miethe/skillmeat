/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BrokerInfo } from './BrokerInfo';
/**
 * Response model for listing available brokers.
 *
 * Contains a list of all configured brokers with their status.
 */
export type BrokerListResponse = {
  /**
   * List of available brokers
   */
  brokers: Array<BrokerInfo>;
};
