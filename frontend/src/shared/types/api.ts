export interface ApiMeta {
  page: number;
  total: number;
  per_page: number;
  total_pages: number;
}

export interface ApiError {
  code: string;
  message: string;
  field?: string;
}

export interface ApiResponse<T> {
  status: 'ok' | 'error';
  data: T;
  meta?: ApiMeta;
  errors?: ApiError[];
}

/** Paginated response — data is always an array */
export interface ApiListResponse<T> extends ApiResponse<T[]> {
  meta: ApiMeta;
}
