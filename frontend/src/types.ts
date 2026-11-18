export type Category = 'bat' | 'bowl';
export type ComponentKey = 'pressure' | 'consistency' | 'adaptability' | 'efficiency' | 'confidence';
export interface Player {
  id: number; name: string; category: Category; rank: number; score: number;
  score_low: number | null; score_high: number | null; impact_low: number | null; impact_high: number | null;
  components: Record<ComponentKey, number> & { match_impact: null };
  role: string; style: string; teams: string[]; competitions: string[]; families: string[]; seasons: number[]; last_seen: string;
  metrics: { balls:number; runs:number; wickets:number; innings:number; high_balls:number; high_innings:number; high_runs:number; high_wickets:number; high_rate:number; normal_rate:number; high_dot_pct:number; high_boundary_pct:number; overall_rate:number; pressure_impact:number; pressure_lift:number; high_dismissal_rate:number };
  phases: { phase:string; balls:number; runs:number; wickets:number; rate:number; impact:number }[];
  pressure_matches: { match_id:number; innings:number; date:string; competition:string; balls:number; runs:number; wickets:number; impact:number; source_rows:number[] }[];
  fit:string; risk:string; recommendation:string; availability:string; strength:string;
  stability: { top10_weight_frequency:number; weight_rank_min:number; weight_rank_max:number };
  public_research: { title:string; url:string; note:string; accessed:string }[];
}
export interface Snapshot {
  overview: { source_deliveries:number; source_matches:number; metadata_matches:number; valid_innings:number; valid_matches:number; valid_delivery_events:number; legal_model_deliveries:number; players_observed:number; ranked_batters:number; ranked_bowlers:number; competitions:number; high_batting_balls:number; high_bowling_balls:number; source_date_min:string; source_date_max:string; missing_match_deliveries:number; exclusions_overlapping:Record<string,number>; seasons:number[]; families:string[]; model_version:string };
  rankings: Record<Category, Player[]>;
  pressure: {category:Category;phase:string;pressure:string;balls:number;runs:number;wickets:number;rate:number}[];
  methodology: { bat_rules:string[]; bowl_rules:string[]; moderate_rules:string; baseline:string; quality:string; normal_comparator:string; components:Record<string,string>; weights:Record<ComponentKey,number>; eligibility:Record<Category,Record<string,number>>; metric_scope:string; uncertainty:string; limitations:string[]; [key:string]:unknown };
  validation: Record<Category, {eligible_players:number; threshold_tests:{scenario:string;top10_overlap:number;top10:string[]}[]; chronological_holdout:{common_players:number;spearman:number|null;interpretation:string}; ipl_only:{eligible_players:number;top10_overlap:number;top10:string[]};higher_opportunity_gate:{eligible_players:number;top10_overlap:number};conventional_rate_spearman:number}>;
  research: {title:string;url:string;note:string;accessed:string}[];
  dashboard_url:string|null;
}
