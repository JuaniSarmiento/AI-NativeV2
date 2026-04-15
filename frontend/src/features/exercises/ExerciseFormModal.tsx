import { useState, type FormEvent } from 'react';
import { useExercisesStore } from './store';
import Button from '@/shared/components/Button';
import Input from '@/shared/components/Input';
import Modal from '@/shared/components/Modal';
import type { ExerciseDifficulty } from './types';

interface ExerciseFormModalProps {
  open: boolean;
  onClose: () => void;
  courseId: string;
  onCreated: () => void;
}

export default function ExerciseFormModal({ open, onClose, courseId, onCreated }: ExerciseFormModalProps) {
  const createExercise = useExercisesStore((s) => s.createExercise);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [difficulty, setDifficulty] = useState<ExerciseDifficulty>('easy');
  const [topicTags, setTopicTags] = useState('');
  const [starterCode, setStarterCode] = useState('');
  const [testInput, setTestInput] = useState('');
  const [testOutput, setTestOutput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createExercise(courseId, {
        title,
        description,
        difficulty,
        topic_tags: topicTags.split(',').map((t) => t.trim()).filter(Boolean),
        starter_code: starterCode,
        test_cases: {
          language: 'python',
          timeout_ms: 10000,
          memory_limit_mb: 128,
          cases: [
            {
              id: 'tc-001',
              description: 'Caso principal',
              input: testInput,
              expected_output: testOutput,
              is_hidden: false,
              weight: 1.0,
            },
          ],
        },
      });
      onClose();
      setTitle('');
      setDescription('');
      setTopicTags('');
      setStarterCode('');
      setTestInput('');
      setTestOutput('');
      onCreated();
    } catch {
      setError('No se pudo crear el ejercicio.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Crear ejercicio" maxWidth="max-w-xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-[8px] border border-[#9F2F2D]/20 bg-[#FDEBEC] px-4 py-3 text-[0.8125rem] text-[#9F2F2D]">
            {error}
          </div>
        )}

        <Input
          label="Titulo"
          placeholder="Hola Mundo y tipos de datos"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <div className="space-y-1.5">
          <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
            Enunciado
          </label>
          <textarea
            required
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe el ejercicio..."
            className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
              Dificultad
            </label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as ExerciseDifficulty)}
              className="h-11 w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-[0.9375rem] text-[var(--color-text-primary)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10"
            >
              <option value="easy">Facil</option>
              <option value="medium">Medio</option>
              <option value="hard">Dificil</option>
            </select>
          </div>
          <Input
            label="Topics (separados por coma)"
            placeholder="variables, strings"
            value={topicTags}
            onChange={(e) => setTopicTags(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-[0.8125rem] font-medium text-[var(--color-text-primary)]">
            Codigo inicial
          </label>
          <textarea
            rows={3}
            value={starterCode}
            onChange={(e) => setStarterCode(e.target.value)}
            placeholder="# Tu codigo aca"
            className="w-full rounded-[8px] border border-[var(--color-border)] bg-[var(--color-neutral-950)] px-3.5 py-2.5 font-mono text-[0.8125rem] text-[var(--color-neutral-300)] outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] placeholder:text-[var(--color-neutral-600)] focus:border-[var(--color-neutral-400)] focus:ring-2 focus:ring-[var(--color-neutral-400)]/10"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Test: entrada"
            placeholder="maria"
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
          />
          <Input
            label="Test: salida esperada"
            placeholder="Hola, MARIA!"
            required
            value={testOutput}
            onChange={(e) => setTestOutput(e.target.value)}
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" size="md" type="button" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" size="md" type="submit" loading={submitting}>
            Crear ejercicio
          </Button>
        </div>
      </form>
    </Modal>
  );
}
