import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { Category, Document } from '../types';

interface CategoryCardsProps {
  documents: Document[];
  selectedCategory: Category;
  onSelectCategory: (category: Category) => void;
}

interface CategoryConfig {
  name: Category;
  icon: React.ReactNode;
  bgColor: string;
  borderColor: string;
  textColor: string;
  iconColor: string;
}

const categories: CategoryConfig[] = [
  {
    name: 'Referral',
    icon: <CheckCircle className="w-6 h-6" />,
    bgColor: 'bg-green-50',
    borderColor: 'border-green-300',
    textColor: 'text-green-800',
    iconColor: 'text-green-600',
  },
  {
    name: 'Incomplete',
    icon: <AlertTriangle className="w-6 h-6" />,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-300',
    textColor: 'text-yellow-800',
    iconColor: 'text-yellow-600',
  },
  {
    name: 'Not Referral',
    icon: <XCircle className="w-6 h-6" />,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
    textColor: 'text-red-800',
    iconColor: 'text-red-600',
  },
];

export default function CategoryCards({ documents, selectedCategory, onSelectCategory }: CategoryCardsProps) {
  const getCategoryStats = (category: Category) => {
    const categoryDocs = documents.filter((d) => d.category === category);
    const count = categoryDocs.length;
    const avgConfidence = count > 0
      ? Math.round(categoryDocs.reduce((sum, d) => sum + d.confidence, 0) / count)
      : 0;
    return { count, avgConfidence };
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {categories.map((cat) => {
        const stats = getCategoryStats(cat.name);
        const isSelected = selectedCategory === cat.name;

        return (
          <button
            key={cat.name}
            onClick={() => onSelectCategory(cat.name)}
            className={`
              p-5 rounded-xl border-2 transition-all duration-200 text-left
              ${cat.bgColor} ${cat.borderColor}
              ${isSelected ? 'ring-2 ring-offset-2 ring-blue-500 shadow-lg scale-[1.02]' : 'hover:shadow-md hover:scale-[1.01]'}
            `}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className={`flex items-center gap-2 ${cat.iconColor}`}>
                  {cat.icon}
                  <span className={`text-lg font-semibold ${cat.textColor}`}>
                    {cat.name}
                  </span>
                </div>
                <p className={`text-3xl font-bold mt-2 ${cat.textColor}`}>
                  {stats.count}
                  <span className="text-base font-normal ml-1">docs</span>
                </p>
              </div>
              {stats.count > 0 && (
                <div className={`text-right ${cat.textColor}`}>
                  <p className="text-sm opacity-75">Avg Confidence</p>
                  <p className="text-xl font-semibold">{stats.avgConfidence}%</p>
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
