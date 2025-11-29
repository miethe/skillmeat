/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TrendDataPoint } from './TrendDataPoint';
/**
 * Response for usage trends over time.
 *
 * Provides time-series data for usage patterns and trends.
 */
export type TrendsResponse = {
  /**
   * Aggregation period (hour, day, week, month)
   */
  period_type: string;
  /**
   * Start of trend period
   */
  start_date: string;
  /**
   * End of trend period
   */
  end_date: string;
  /**
   * Time-series data points
   */
  data_points: Array<TrendDataPoint>;
  /**
   * Number of periods in the response
   */
  total_periods: number;
};
