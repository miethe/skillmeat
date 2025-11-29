import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Project Entity Management | SkillMeat',
  description: 'Manage entities deployed to your project',
};

export default function ProjectManageLayout({ children }: { children: React.ReactNode }) {
  return children;
}
