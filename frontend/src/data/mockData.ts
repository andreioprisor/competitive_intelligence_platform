export const MOCK_COMPANY_DATA = {
    domain: 'uipath.com',
    logoUrl: 'https://logo.clearbit.com/uipath.com',
    description: 'UiPath is a leading robotic process automation (RPA) software company.',
    strategies: [
        'Market Expansion',
        'Product Innovation',
        'Strategic Acquisitions',
        'Cloud-First Approach'
    ],
    geography: 'Global (North America, Europe, Asia Pacific)',
    domainOfActivity: 'Robotic Process Automation (RPA) & AI',
    employees: '4,000+',
    differentiators: 'End-to-end automation platform, strong community, AI-powered discovery.',
    services: 'RPA Platform, Process Mining, Task Mining, Document Understanding',
    marketShare: '35%',
    growthRate: '15% YoY',
    marketCap: '$10.4B',
    revenue: '$1.1B',
    foundedYear: 2005
};

export const MOCK_COMPETITORS = [
    {
        name: 'Automation Anywhere',
        logoUrl: 'https://logo.clearbit.com/automationanywhere.com',
        description: 'A developer of robotic process automation software.',
        strategies: ['Cloud-Native Platform', 'AI Integration'],
        category: 'Direct',
        employees: '3,000+',
        marketCap: '$6.8B',
        revenue: '$600M',
        foundedYear: 2003,
        solutions: ['Automation 360', 'IQ Bot', 'Bot Insight']
    },
    {
        name: 'Blue Prism',
        logoUrl: 'https://logo.clearbit.com/blueprism.com',
        description: 'Intelligent automation platform for enterprise.',
        strategies: ['Enterprise Focus', 'Security-First'],
        category: 'Direct',
        employees: '2,500+',
        marketCap: '$1.5B',
        revenue: '$200M',
        foundedYear: 2001,
        solutions: ['Blue Prism Platform', 'Decipher IDP', 'Process Intelligence']
    },
    {
        name: 'Microsoft Power Automate',
        logoUrl: 'https://logo.clearbit.com/microsoft.com',
        description: 'Low-code automation platform integrated with Microsoft 365.',
        strategies: ['Ecosystem Integration', 'Low-Code'],
        category: 'Indirect',
        employees: '221,000+',
        marketCap: '$3.1T',
        revenue: '$211B',
        foundedYear: 1975,
        solutions: ['Power Automate Desktop', 'Power Automate Cloud', 'AI Builder']
    },
    {
        name: 'Pegasystems',
        logoUrl: 'https://logo.clearbit.com/pega.com',
        description: 'Low-code platform for workflow automation and case management.',
        strategies: ['BPM Integration', 'Case Management'],
        category: 'Emerging',
        employees: '6,500+',
        marketCap: '$4.2B',
        revenue: '$1.4B',
        foundedYear: 1983
    },
    {
        name: 'Nice Systems',
        logoUrl: 'https://logo.clearbit.com/nice.com',
        description: 'Customer engagement and workforce optimization solutions.',
        strategies: ['Contact Center Focus', 'Analytics'],
        category: 'Emerging',
        employees: '8,000+',
        marketCap: '$13.5B',
        revenue: '$2.1B',
        foundedYear: 1986
    },
    {
        name: 'WorkFusion',
        logoUrl: 'https://logo.clearbit.com/workfusion.com',
        description: 'AI-powered intelligent automation for enterprises.',
        strategies: ['AI-First', 'Industry Solutions'],
        category: 'Indirect',
        employees: '600+',
        marketCap: '$1.2B',
        revenue: '$80M',
        foundedYear: 2010
    },
    {
        name: 'Zapier',
        logoUrl: 'https://logo.clearbit.com/zapier.com',
        description: 'Web-based automation tool connecting apps and services.',
        strategies: ['SMB Focus', 'App Integrations'],
        category: 'Indirect',
        employees: '800+',
        marketCap: '$5.0B',
        revenue: '$140M',
        foundedYear: 2011
    },
    {
        name: 'Salesforce MuleSoft',
        logoUrl: 'https://logo.clearbit.com/salesforce.com',
        description: 'Integration platform with growing automation capabilities.',
        strategies: ['API-Led Connectivity', 'Customer 360'],
        category: 'Emerging',
        employees: '73,000+',
        marketCap: '$280B',
        revenue: '$34.9B',
        foundedYear: 1999
    },
    {
        name: 'IBM',
        logoUrl: 'https://logo.clearbit.com/ibm.com',
        description: 'Offers RPA as part of its Cloud Pak for Business Automation.',
        strategies: ['AI-Powered Automation', 'Hybrid Cloud'],
        category: 'Emerging',
        employees: '282,000+',
        marketCap: '$175B',
        revenue: '$60.5B',
        foundedYear: 1911
    }
];

export const MOCK_SOLUTIONS = [
    {
        name: 'Finance Automation',
        industries: ['Banking', 'Insurance', 'FinTech'],
        partners: ['Deloitte', 'PwC', 'KPMG']
    },
    {
        name: 'Healthcare Bot',
        industries: ['Hospitals', 'Pharmaceuticals'],
        partners: ['Cerner', 'Epic']
    },
    {
        name: 'Supply Chain Optimizer',
        industries: ['Logistics', 'Retail', 'Manufacturing'],
        partners: ['SAP', 'Oracle']
    },
    {
        name: 'HR Onboarding Assistant',
        industries: ['All Industries'],
        partners: ['Workday', 'ADP']
    }
];

export const MOCK_TIMELINE_ALERTS = [
    {
        id: 1,
        competitor: 'Microsoft Power Automate',
        channel: 'News Search',
        title: 'Microsoft announces Power Automate Desktop now free for Windows 11 users',
        description: 'Microsoft has made Power Automate Desktop available at no additional cost for all Windows 11 users, expanding its automation capabilities to millions of devices.',
        date: '2025-11-20T10:30:00Z',
        source: 'TechCrunch'
    },
    {
        id: 2,
        competitor: 'Automation Anywhere',
        channel: 'Jobs Posting',
        title: 'Automation Anywhere hiring 50+ engineers in India',
        description: 'Multiple job postings indicate Automation Anywhere is expanding its R&D team in Bangalore, focusing on AI and machine learning capabilities.',
        date: '2025-11-19T14:20:00Z',
        source: 'LinkedIn Jobs'
    },
    {
        id: 3,
        competitor: 'Blue Prism',
        channel: 'Pricing Intelligence',
        title: 'Blue Prism reduces enterprise license pricing by 15%',
        description: 'Competitive pricing analysis shows Blue Prism has lowered its enterprise tier pricing, likely in response to market pressure.',
        date: '2025-11-18T09:15:00Z',
        source: 'Pricing Monitor'
    },
    {
        id: 4,
        competitor: 'Zapier',
        channel: 'Social Media',
        title: 'Zapier launches AI-powered workflow suggestions',
        description: 'Zapier announced on Twitter a new AI feature that automatically suggests workflow automations based on user behavior and connected apps.',
        date: '2025-11-17T16:45:00Z',
        source: 'Twitter/X'
    },
    {
        id: 5,
        competitor: 'Automation Anywhere',
        channel: 'Website Monitoring',
        title: 'New case study: Fortune 500 bank deployment',
        description: 'Automation Anywhere added a case study showcasing a major US bank processing 2M transactions monthly using Automation 360.',
        date: '2025-11-16T11:00:00Z',
        source: 'automationanywhere.com'
    },
    {
        id: 6,
        competitor: 'Microsoft Power Automate',
        channel: 'Reddit/X Search',
        title: 'Users reporting improved AI Builder performance',
        description: 'Multiple Reddit threads discuss significant performance improvements in Power Automate AI Builder, with 3x faster model training times.',
        date: '2025-11-15T13:30:00Z',
        source: 'r/PowerAutomate'
    },
    {
        id: 7,
        competitor: 'WorkFusion',
        channel: 'News Search',
        title: 'WorkFusion secures $50M Series D funding',
        description: 'WorkFusion announced a $50M funding round led by Accel Partners to expand its AI-powered automation platform for financial services.',
        date: '2025-11-14T08:00:00Z',
        source: 'VentureBeat'
    },
    {
        id: 8,
        competitor: 'Blue Prism',
        channel: 'Google Search Ads',
        title: 'Increased ad spend on "RPA enterprise" keywords',
        description: 'Blue Prism has increased Google Ads budget by 40% for enterprise RPA keywords, appearing in top positions for high-value searches.',
        date: '2025-11-13T10:20:00Z',
        source: 'Ad Intelligence'
    },
    {
        id: 9,
        competitor: 'Zapier',
        channel: 'Social Media',
        title: 'Zapier reaches 7 million users milestone',
        description: 'CEO announced on LinkedIn that Zapier has surpassed 7 million users, with 50% growth in enterprise customers year-over-year.',
        date: '2025-11-12T15:00:00Z',
        source: 'LinkedIn'
    },
    {
        id: 10,
        competitor: 'Automation Anywhere',
        channel: 'News Search',
        title: 'Partnership with Salesforce announced',
        description: 'Automation Anywhere and Salesforce announce strategic partnership to integrate Automation 360 with Salesforce Customer 360.',
        date: '2025-11-11T09:30:00Z',
        source: 'Business Wire'
    }
];
