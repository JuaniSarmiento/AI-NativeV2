export interface RunResult {
  stdout: string;
  stderr: string;
  exit_code: number;
  runtime_ms: number;
  status: string;
}
