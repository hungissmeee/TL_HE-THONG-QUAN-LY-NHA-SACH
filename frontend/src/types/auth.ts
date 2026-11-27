export interface EmployeeSummary {
  employee_code: string;
  full_name: string;
  role: string;
  role_code: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: EmployeeSummary;
}

export interface LoginCredentials {
  username: string;
  password: string;
}
