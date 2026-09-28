-- Hosted storage for the trace error-analysis app (run once in the Supabase SQL editor,
-- or via `psql "$DATABASE_URL" -f supabase/schema.sql`). Safe to re-run.
--
-- Anyone can read workspaces and their data (the site is public). Writes only go through
-- the SECURITY DEFINER functions below, which check the workspace passcode server-side.
-- Passcode hashes live in a table no public role can read.

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.trace_workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 80),
  is_example boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.trace_workspace_secrets (
  workspace_id uuid primary key references public.trace_workspaces on delete cascade,
  passcode_hash text not null
);

create table if not exists public.trace_workspace_data (
  workspace_id uuid not null references public.trace_workspaces on delete cascade,
  kind text not null check (kind in ('samples', 'annotations', 'graph', 'patterns', 'suggestions')),
  data jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (workspace_id, kind)
);

alter table public.trace_workspaces enable row level security;
alter table public.trace_workspace_secrets enable row level security;
alter table public.trace_workspace_data enable row level security;

drop policy if exists "public read" on public.trace_workspaces;
create policy "public read" on public.trace_workspaces for select using (true);
drop policy if exists "public read" on public.trace_workspace_data;
create policy "public read" on public.trace_workspace_data for select using (true);
-- trace_workspace_secrets: RLS on, no policies => unreadable through the API.

create or replace function public._trace_passcode_ok(p_workspace uuid, p_passcode text)
returns boolean language sql stable security definer set search_path = public, extensions as $$
  select exists (
    select 1 from trace_workspace_secrets
    where workspace_id = p_workspace and passcode_hash = crypt(coalesce(p_passcode, ''), passcode_hash)
  );
$$;

create or replace function public.check_trace_passcode(p_workspace uuid, p_passcode text)
returns boolean language sql stable security definer set search_path = public, extensions as $$
  select _trace_passcode_ok(p_workspace, p_passcode);
$$;

create or replace function public.create_trace_workspace(p_name text, p_passcode text, p_samples jsonb, p_graph jsonb)
returns uuid language plpgsql security definer set search_path = public, extensions as $$
declare new_id uuid;
begin
  if char_length(coalesce(p_passcode, '')) < 4 then raise exception 'Passcode must be at least 4 characters'; end if;
  if jsonb_typeof(p_samples) <> 'array' or jsonb_array_length(p_samples) = 0 then raise exception 'No traces found'; end if;
  if pg_column_size(p_samples) + pg_column_size(p_graph) > 5000000 then raise exception 'Traces file is too large (5 MB max)'; end if;
  insert into trace_workspaces (name) values (trim(p_name)) returning id into new_id;
  insert into trace_workspace_secrets values (new_id, crypt(p_passcode, gen_salt('bf')));
  insert into trace_workspace_data (workspace_id, kind, data) values
    (new_id, 'samples', p_samples), (new_id, 'graph', p_graph),
    (new_id, 'annotations', '{}'::jsonb), (new_id, 'patterns', '[]'::jsonb), (new_id, 'suggestions', '[]'::jsonb);
  return new_id;
end;
$$;

create or replace function public.save_trace_data(p_workspace uuid, p_passcode text, p_kind text, p_data jsonb)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  if not _trace_passcode_ok(p_workspace, p_passcode) then raise exception 'Wrong passcode'; end if;
  if p_kind not in ('annotations', 'patterns', 'suggestions') then raise exception 'That data is read-only'; end if;
  if pg_column_size(p_data) > 5000000 then raise exception 'Too much data (5 MB max)'; end if;
  insert into trace_workspace_data (workspace_id, kind, data, updated_at) values (p_workspace, p_kind, p_data, now())
  on conflict (workspace_id, kind) do update set data = excluded.data, updated_at = now();
end;
$$;

revoke all on function public._trace_passcode_ok(uuid, text) from public, anon, authenticated;
grant execute on function public.check_trace_passcode(uuid, text) to anon, authenticated;
grant execute on function public.create_trace_workspace(text, text, jsonb, jsonb) to anon, authenticated;
grant execute on function public.save_trace_data(uuid, text, text, jsonb) to anon, authenticated;
