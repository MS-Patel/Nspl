export interface User {
  id: number;
  username: string;
  name: string;
  email: string;
  role: 'ADMIN' | 'RM' | 'DISTRIBUTOR' | 'INVESTOR';
}
