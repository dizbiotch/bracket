import {
  Anchor,
  Button,
  Container,
  Group,
  Paper,
  PasswordInput,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { showNotification } from '@mantine/notifications';
import { IconArrowLeft, IconCheck } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router';

import { requestPasswordReset, resetPassword } from '@services/user';

export default function PasswordResetPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [resetToken, setResetToken] = useState<string>(searchParams.get('token') ?? '');
  const [step, setStep] = useState<'request' | 'reset'>(resetToken ? 'reset' : 'request');

  const requestForm = useForm({
    initialValues: {
      email: '',
    },
    validate: {
      email: (value) => (/^\S+@\S+$/.test(value) ? null : t('invalid_email_validation')),
    },
  });

  const resetForm = useForm({
    initialValues: {
      token: resetToken,
      new_password: '',
      confirm_password: '',
    },
    validate: {
      token: (value) => (value.length > 0 ? null : t('token_required_validation')),
      new_password: (value) =>
        value.length >= 8 ? null : t('invalid_password_validation'),
      confirm_password: (value, values) =>
        value === values.new_password ? null : t('passwords_do_not_match_validation'),
    },
  });

  async function handleRequestReset(values: { email: string }) {
    const response = await requestPasswordReset(values.email);

    // If backend returns a reset_token (dev mode), prefill it for convenience.
    if (response && response.data && response.data.reset_token) {
      setResetToken(response.data.reset_token);
      resetForm.setFieldValue('token', response.data.reset_token);
    }

    showNotification({
      color: 'green',
      title: t('password_reset_request_sent_title') ?? 'If this email exists, a reset link was sent',
      message: '',
      icon: <IconCheck />,
    });

    setStep('reset');
  }

  async function handleResetPassword(values: {
    token: string;
    new_password: string;
    confirm_password: string;
  }) {
    const response = await resetPassword(values.token, values.new_password);
    if (!response || response.name === 'AxiosError') {
      return;
    }

    showNotification({
      color: 'green',
      title: t('password_reset_success_title') ?? 'Password has been reset',
      message: '',
      icon: <IconCheck />,
    });

    navigate('/login');
  }

  return (
    <Container size={460} my={30}>
      <Title ta="center" mb="xs">
        {step === 'request' ? t('forgot_password_title') ?? 'Forgot your password?' : t('reset_password_title') ?? 'Reset your password'}
      </Title>
      <Text c="dimmed" size="sm" ta="center" mb="md">
        {step === 'request'
          ? t('forgot_password_description') ?? 'Enter your email address to request a reset link.'
          : t('reset_password_description') ?? 'Enter the reset token and your new password.'}
      </Text>

      <Paper withBorder shadow="md" p={30} radius="md" mt="xl">
        {step === 'request' ? (
          <form onSubmit={requestForm.onSubmit(handleRequestReset)}>
            <TextInput
              label={t('email_input_label')}
              placeholder={t('email_input_placeholder')}
              required
              mb="md"
              {...requestForm.getInputProps('email')}
            />

            <Group justify="space-between" mt="lg">
              <Anchor<'a'> size="sm" onClick={() => navigate('/login')}>
                <IconArrowLeft size={12} style={{ marginRight: 4 }} />
                {t('back_to_login_button') ?? 'Back to login'}
              </Anchor>
              <Button type="submit">
                {t('request_reset_button') ?? 'Request reset'}
              </Button>
            </Group>
          </form>
        ) : (
          <form onSubmit={resetForm.onSubmit(handleResetPassword)}>
            <TextInput
              label={t('reset_token_label') ?? 'Reset token'}
              placeholder={t('reset_token_placeholder') ?? 'Paste your reset token'}
              required
              mb="md"
              {...resetForm.getInputProps('token')}
            />
            <PasswordInput
              label={t('new_password_label') ?? 'New password'}
              placeholder={t('new_password_placeholder') ?? 'Enter new password'}
              required
              mb="md"
              {...resetForm.getInputProps('new_password')}
            />
            <PasswordInput
              label={t('confirm_password_label') ?? 'Confirm password'}
              placeholder={t('confirm_password_placeholder') ?? 'Repeat new password'}
              required
              mb="md"
              {...resetForm.getInputProps('confirm_password')}
            />

            <Group justify="space-between" mt="lg">
              <Anchor<'a'> size="sm" onClick={() => navigate('/login')}>
                <IconArrowLeft size={12} style={{ marginRight: 4 }} />
                {t('back_to_login_button') ?? 'Back to login'}
              </Anchor>
              <Button type="submit">
                {t('reset_password_button') ?? 'Reset password'}
              </Button>
            </Group>
          </form>
        )}
      </Paper>
    </Container>
  );
}
