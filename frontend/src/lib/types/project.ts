export interface Project {
  id: string; // uuid
  name: string;
  owner_id: string; // uuid - The project owner
  created_at: string; // date-time
  updated_at: string; // date-time
}
