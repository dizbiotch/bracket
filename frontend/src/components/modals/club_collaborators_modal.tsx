import { Badge, Button, Group, Modal, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { BiUserPlus } from '@react-icons/all-files/bi/BiUserPlus';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Club } from '@openapi';
import { addClubCollaborator, getClubCollaborators, removeClubCollaborator } from '@services/club';

export default function ClubCollaboratorsModal({ club }: { club: Club }) {
  const { t } = useTranslation();
  const [opened, setOpened] = useState(false);
  const collaborators = getClubCollaborators(club.id);

  const form = useForm({
    initialValues: {
      email: '',
    },
    validate: {
      email: (value) => (/^\S+@\S+$/.test(value) ? null : t('invalid_email_validation')),
    },
  });

  async function onSubmit(values: { email: string }) {
    await addClubCollaborator(club.id, values.email);
    await collaborators.mutate();
    setOpened(false);
    form.reset();
  }

  return (
    <>
      <Button
        color="blue"
        size="xs"
        style={{ marginRight: 10 }}
        onClick={() => setOpened(true)}
        leftSection={<BiUserPlus size={18} />}
      >
        {t('invite_collaborator_button')}
      </Button>

      <Modal opened={opened} onClose={() => setOpened(false)} title={t('invite_collaborator_title')}>
        <Stack gap="md">
          <Text size="sm">
            {t('invite_collaborator_description')}
          </Text>

          <form onSubmit={form.onSubmit(onSubmit)}>
            <TextInput
              withAsterisk
              label={t('email_input_label')}
              placeholder={t('email_input_placeholder')}
              {...form.getInputProps('email')}
            />
            <Button fullWidth style={{ marginTop: 10 }} color="green" type="submit">
              {t('send_invitation_button')}
            </Button>
          </form>

          <Text fw={500} size="sm">
            {t('current_collaborators_title') ?? 'People with access'}
          </Text>
          <Stack gap={4}>
            {collaborators.data?.data?.map((user: any) => (
              <Group key={user.id} justify="space-between">
                <div>
                  <Text size="sm">{user.name}</Text>
                  <Text size="xs" c="dimmed">
                    {user.email}
                  </Text>
                </div>
                <Group gap="xs">
                  {user.account_type && (
                    <Badge size="xs" variant="light">
                      {user.account_type}
                    </Badge>
                  )}
                  <Button
                    size="xs"
                    color="red"
                    variant="subtle"
                    onClick={async () => {
                      await removeClubCollaborator(club.id, user.id);
                      await collaborators.mutate();
                    }}
                  >
                    {t('remove_collaborator_button') ?? 'Remove'}
                  </Button>
                </Group>
              </Group>
            ))}
            {collaborators.data?.data?.length === 0 && (
              <Text size="xs" c="dimmed">
                {t('no_collaborators_label') ?? 'Only you have access to this club.'}
              </Text>
            )}
          </Stack>
        </Stack>
      </Modal>
    </>
  );
}
