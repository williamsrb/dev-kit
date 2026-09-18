import { H1, Stack, Stat, Text } from 'cursor/canvas';

export default function MinimalCanvas() {
  return (
    <Stack gap={16}>
      <H1>Export fixture</H1>
      <Text>This canvas is used to verify HTML export.</Text>
      <Stat value="42" label="Answer" />
    </Stack>
  );
}
