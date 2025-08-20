import { forwardRef } from 'preact/compat';
import { cn, themeClasses } from '../../lib/theme-config';

interface ThemeAwareCardProps {
  children: preact.ComponentChildren;
  variant?: 'default' | 'elevated' | 'interactive';
  className?: string;
  onClick?: () => void;
}

const ThemeAwareCard = forwardRef<HTMLDivElement, ThemeAwareCardProps>(
  ({ children, variant = 'default', className, onClick }, ref) => {
    const baseClasses = 'rounded-lg p-6 transition-all duration-200';
    const variantClasses = themeClasses.card[variant];
    const interactiveClasses = onClick 
      ? 'cursor-pointer hover:shadow-md dark:hover:shadow-lg transform hover:scale-[1.02]' 
      : '';

    return (
      <div
        ref={ref}
        className={cn(baseClasses, variantClasses, interactiveClasses, className)}
        onClick={onClick}
      >
        {children}
      </div>
    );
  }
);

ThemeAwareCard.displayName = 'ThemeAwareCard';

export default ThemeAwareCard;

// Example usage component
export function ThemeAwareCardExample() {
  return (
    <div className="p-8 space-y-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Theme-Aware Components
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Default Card */}
        <ThemeAwareCard variant="default">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Default Card
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            This is a default card with automatic theme support.
          </p>
        </ThemeAwareCard>

        {/* Elevated Card */}
        <ThemeAwareCard variant="elevated">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Elevated Card
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            This card has enhanced shadow for emphasis.
          </p>
        </ThemeAwareCard>

        {/* Interactive Card */}
        <ThemeAwareCard 
          variant="interactive"
          onClick={() => alert('Card clicked!')}
        >
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Interactive Card
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            This card responds to user interaction.
          </p>
        </ThemeAwareCard>

        {/* Trading Card Example */}
        <ThemeAwareCard variant="elevated" className="border-l-4 border-green-500">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              BTC Position
            </h3>
            <span className="text-green-600 dark:text-green-400 font-medium">
              +5.2%
            </span>
          </div>
          <p className="text-gray-600 dark:text-gray-300">
            Long position with 2x leverage
          </p>
          <div className="mt-4 flex items-center space-x-4">
            <div className="text-sm">
              <span className="text-gray-500 dark:text-gray-400">Entry:</span>
              <span className="ml-1 font-medium text-gray-900 dark:text-white">
                $45,200
              </span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500 dark:text-gray-400">Current:</span>
              <span className="ml-1 font-medium text-gray-900 dark:text-white">
                $47,550
              </span>
            </div>
          </div>
        </ThemeAwareCard>

        {/* Status Card */}
        <ThemeAwareCard variant="interactive">
          <div className="flex items-center space-x-3">
            <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse"></div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                System Status
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                All systems operational
              </p>
            </div>
          </div>
        </ThemeAwareCard>

        {/* AI Confidence Card */}
        <ThemeAwareCard variant="elevated" className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-2">
              87%
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
              AI Confidence
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              High confidence signal
            </p>
          </div>
        </ThemeAwareCard>
      </div>
    </div>
  );
} 