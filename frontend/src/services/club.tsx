import useSWR, { SWRResponse } from 'swr';

import { UserPublicResponse } from '@openapi';
import { createAxios, handleRequestError } from './adapter';

export async function createClub(name: string) {
  return createAxios()
    .post('clubs', { name })
    .catch((response: any) => handleRequestError(response));
}

export async function deleteClub(club_id: number) {
  return createAxios()
    .delete(`clubs/${club_id}`)
    .catch((response: any) => handleRequestError(response));
}

export async function updateClub(club_id: number, name: string) {
  return createAxios()
    .put(`clubs/${club_id}`, {
      name,
    })
    .catch((response: any) => handleRequestError(response));
}

export async function addClubCollaborator(club_id: number, email: string) {
  return createAxios()
    .post(`clubs/${club_id}/collaborators`, { email })
    .catch((response: any) => handleRequestError(response));
}

export async function removeClubCollaborator(club_id: number, user_id: number) {
  return createAxios()
    .delete(`clubs/${club_id}/collaborators/${user_id}`)
    .catch((response: any) => handleRequestError(response));
}

export function getClubCollaborators(club_id: number): SWRResponse<UserPublicResponse> {
  return useSWR(`clubs/${club_id}/collaborators`, (url: string) =>
    createAxios()
      .get(url)
      .then((res: { data: any }) => res.data)
  );
}
