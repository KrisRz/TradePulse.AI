import type { Meta, StoryObj } from '@storybook/preact';
import UserManagementAdmin from '../../components/admin/UserManagementAdmin';

const meta: Meta<typeof UserManagementAdmin> = {
  title: 'Admin/UserManagementAdmin',
  component: UserManagementAdmin,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: `
# UserManagement Component

Comprehensive user administration interface for managing TradePulse.AI users, roles, permissions, and account settings.

## Features
- **User Directory**: Complete list of all registered users with search and filtering
- **Role Management**: Assign and modify user roles (Admin, Trader, Viewer)
- **Permission Control**: Granular permission management for platform features
- **Account Status**: Enable/disable accounts and manage access controls
- **Activity Monitoring**: Track user login activity and platform usage
- **Performance Tracking**: Monitor trading performance and portfolio metrics
- **Bulk Operations**: Mass user operations and data export functionality
- **Security Management**: Password resets, 2FA status, and security settings

## User Roles
- **Admin**: Full system access and user management capabilities
- **Premium Trader**: Advanced trading features and analytics access
- **Basic Trader**: Standard trading features with limited analytics
- **Viewer**: Read-only access to public features and basic analytics
- **Trial User**: Temporary access with limited features

## User Status States
- **🟢 Active**: User account is active and accessible
- **🟡 Suspended**: Account temporarily suspended with limited access
- **🔴 Disabled**: Account disabled and access revoked
- **⚪ Pending**: New account awaiting verification or approval

## Use Cases
- User account administration and support
- Role-based access control management
- User behavior analysis and insights
- Compliance and audit requirements
- Customer support and account troubleshooting
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {},
};

export default meta;
type Story = StoryObj<typeof UserManagement>;

export const Default: Story = {
  parameters: {
    docs: {
      description: {
        story: 'Default UserManagement interface showing active user directory with standard admin controls.'
      }
    }
  }
};

export const LargeUserBase: Story = {
  parameters: {
    docs: {
      description: {
        story: 'UserManagement handling a large user base with pagination, search, and filtering capabilities.'
      }
    }
  }
};

export const RoleManagement: Story = {
  parameters: {
    docs: {
      description: {
        story: 'UserManagement focused on role assignment and permission management interface.'
      }
    }
  }
};

export const UserDetails: Story = {
  parameters: {
    docs: {
      description: {
        story: 'UserManagement with detailed user profile view showing comprehensive account information.'
      }
    }
  }
};

export const SecurityManagement: Story = {
  parameters: {
    docs: {
      description: {
        story: 'UserManagement interface for security administration including 2FA management and password policies.'
      }
    }
  }
};

export const ActivityMonitoring: Story = {
  parameters: {
    docs: {
      description: {
        story: 'UserManagement showing user activity logs and platform usage analytics.'
      }
    }
  }
};

export const SuspendedUsers: Story = {
  parameters: {
    docs: {
      description: {
        story: 'UserManagement displaying suspended or disabled accounts requiring administrative attention.'
      }
    }
  }
};

export const BulkOperations: Story = {
  parameters: {
    docs: {
      description: {
        story: 'UserManagement with bulk selection and mass operation capabilities for efficient administration.'
      }
    }
  }
};

export const MobileView: Story = {
  parameters: {
    viewport: {
      defaultViewport: 'mobile1'
    },
    docs: {
      description: {
        story: 'UserManagement optimized for mobile administration with essential features accessible.'
      }
    }
  }
};

export const AccessibilityTest: Story = {
  parameters: {
    a11y: {
      config: {
        rules: [
          {
            id: 'color-contrast',
            enabled: true,
          },
          {
            id: 'keyboard',
            enabled: true,
          },
          {
            id: 'label',
            enabled: true,
          },
        ],
      },
    },
    docs: {
      description: {
        story: 'UserManagement with accessibility testing for keyboard navigation and screen reader support.'
      }
    }
  }
}; 